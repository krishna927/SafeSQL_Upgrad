"""GPT-4 SQL Generator for SafeSQL framework.

This module implements SQL generation using GPT-4 API with schema-aware prompting
and integration with the Verification Layer.
"""

import os
import json
from typing import Dict, List, Optional
import logging
from pathlib import Path

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

from .base_model import BaseModel
from ..utils.logger import get_logger
from ..utils.sql_identifier import quote_identifier, needs_quoting

logger = get_logger(__name__)

# Load .env file if available
if DOTENV_AVAILABLE:
    project_root = Path(__file__).parent.parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)  # Use override to ensure latest key is loaded


class GPT4SQLGenerator(BaseModel):
    """GPT-4 based SQL generator with schema-aware prompting."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize GPT-4 SQL generator.
        
        Args:
            config: Configuration dictionary with:
                - api_key: OpenAI API key (or use OPENAI_API_KEY env var)
                - model: Model name (default: "gpt-4")
                - temperature: Sampling temperature (default: 0.0)
                - max_tokens: Maximum tokens (default: 512)
        """
        super().__init__(config)
        
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI library not installed. Install with: pip install openai>=1.12.0"
            )
        
        # Get API key from config or environment
        api_key = self.config.get("api_key") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key in config."
            )
        
        self.client = OpenAI(api_key=api_key)
        # Default to gpt-4o (cheaper and better than legacy GPT-4)
        # Can also use "gpt-4", "gpt-4-turbo", or "gpt-4o-mini" if needed
        self.model = self.config.get("model", "gpt-4o")
        self.temperature = self.config.get("temperature", 0.0)
        self.max_tokens = self.config.get("max_tokens", 512)
        
        logger.info(f"GPT4SQLGenerator initialized with model: {self.model}")
    
    def generate(
        self,
        prompt: str,
        schema: Optional[Dict] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        guardrails: Optional[object] = None,
        db_connection=None,
        **kwargs
    ) -> str:
        """
        Generate SQL query from natural language prompt.
        
        Args:
            prompt: Natural language query
            schema: Database schema dictionary
            max_tokens: Maximum tokens to generate (overrides config)
            temperature: Sampling temperature (overrides config)
            guardrails: Optional Guardrails instance for safety checks
            **kwargs: Additional generation parameters
            
        Returns:
            Generated SQL query string
        """
        # Build prompt with schema and safety constraints
        full_prompt = self._build_prompt(prompt, schema)
        
        # Apply guardrails to prompt if available
        if guardrails:
            full_prompt = guardrails.build_safe_prompt(full_prompt, schema)
        
        # Generate SQL
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self._get_system_prompt(schema)},
                {"role": "user", "content": full_prompt}
            ],
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            **kwargs
        )
        
        sql = response.choices[0].message.content.strip()
        
        # Clean up SQL (remove markdown code blocks if present)
        sql = self._clean_sql(sql)
        
        # Fix generic table names (CRITICAL FIX for Spider)
        if schema:
            sql = self._fix_generic_table_name(sql, schema)
        
        # Fix column names (DISABLED - reduces accuracy from 50% to 20%)
        # TODO: Consider prompt-engineering-based column alignment if re-enabled.
        # if schema:
        #     # Get db_connection from kwargs if not passed directly
        #     conn = db_connection or kwargs.get('db_connection')
        #     # Only fix if we have DB connection and it's Spider
        #     is_spider = (schema.get("database_name") and schema.get("database_name") != "wikisql_value") or \
        #                (schema.get("metadata", {}).get("source") == "Spider")
        #     if is_spider and conn:
        #         sql = self._fix_column_names(sql, schema, conn)
        
        # Fix identifier quoting for schema columns/tables
        if schema:
            sql = self._fix_identifier_quoting(sql, schema)
        
        # Apply guardrails filtering if available
        if guardrails:
            guardrails_result = guardrails.apply_guardrails(sql)
            if not guardrails_result["safe"]:
                logger.warning(f"Unsafe SQL detected by guardrails: {guardrails_result['violations']}")
                # In production, might reject or regenerate here
                # For now, log the violation
        
        logger.debug(f"Generated SQL: {sql}")
        return sql
    
    def generate_batch(
        self,
        prompts: List[str],
        schemas: Optional[List[Dict]] = None,
        **kwargs
    ) -> List[str]:
        """
        Generate SQL queries for multiple prompts.
        
        Args:
            prompts: List of natural language queries
            schemas: List of database schemas (one per prompt)
            **kwargs: Additional generation parameters
            
        Returns:
            List of generated SQL queries
        """
        results = []
        schemas = schemas or [None] * len(prompts)
        
        for prompt, schema in zip(prompts, schemas):
            try:
                sql = self.generate(prompt, schema, **kwargs)
                results.append(sql)
            except Exception as e:
                logger.error(f"Error generating SQL for prompt: {prompt[:50]}... Error: {e}")
                results.append("")  # Return empty string on error
        
        return results
    
    def _build_prompt(self, question: str, schema: Optional[Dict]) -> str:
        """
        Build prompt with schema information and few-shot examples.
        
        Args:
            question: Natural language question
            schema: Database schema dictionary
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        
        # Add schema information
        if schema:
            prompt_parts.append("## Database Schema:")
            prompt_parts.append(self._format_schema(schema))
            prompt_parts.append("")
        
        # Add few-shot examples
        prompt_parts.append("## Examples:")
        prompt_parts.append(self._get_few_shot_examples(schema))
        prompt_parts.append("")
        
        # Add the actual question
        prompt_parts.append("## Question:")
        prompt_parts.append(question)
        prompt_parts.append("")
        prompt_parts.append("## SQL Query:")
        
        return "\n".join(prompt_parts)
    
    def _format_schema(self, schema: Dict) -> str:
        """
        Format schema information for prompt.
        
        Args:
            schema: Schema dictionary
            
        Returns:
            Formatted schema string
        """
        parts = []
        
        # Detect WikiSQL_VALUE dataset (uses generic column names in database)
        is_wikisql = schema.get("database_name") == "wikisql_value" or \
                     any(col.get("db_name") for col in schema.get("columns", []))
        
        # Table name (handle both 'name' and 'table_name' keys)
        # For Spider, handle multi-table schemas
        is_spider = schema.get("database_name") and schema.get("database_name") != "wikisql_value"
        if is_spider and "tables" in schema:
            # Multi-table schema (Spider)
            table_names = schema.get("table_names", [])
            if table_names:
                parts.append("=" * 50)
                parts.append("CRITICAL: AVAILABLE TABLES IN THIS DATABASE")
                parts.append("=" * 50)
                for i, tbl_name in enumerate(table_names, 1):
                    parts.append(f"  Table {i}: {tbl_name}")
                parts.append("")
                parts.append("IMPORTANT: Use the EXACT table names listed above in your SQL queries.")
                parts.append("DO NOT use generic names like 'table' or 'Table'.")
                parts.append("")
        else:
            # Single-table schema
            table_name = schema.get("table_name") or schema.get("name", "table")
            parts.append("=" * 50)
            parts.append(f"CRITICAL: TABLE NAME = {table_name}")
            parts.append("=" * 50)
            parts.append(f"IMPORTANT: Use this EXACT table name: {table_name}")
            parts.append("DO NOT use generic names like 'table' or 'Table'.")
            parts.append("")
        
        # Columns
        columns = schema.get("columns", [])
        if columns:
            if is_wikisql:
                # WikiSQL_VALUE: Use database column names with mapping
                parts.append("IMPORTANT: Use database column names (col0, col1, col2, etc.) in your SQL queries.")
                parts.append("Column Mapping:")
                for col in columns:
                    db_name = col.get("db_name", f"col{col.get('index', 0)}")
                    human_name = col.get("name", "")
                    col_type = col.get("type", "")
                    parts.append(f"  - {db_name} ({col_type}) - represents: {human_name}")
            else:
                # Spider or other datasets: Use schema column names
                # For Spider multi-table, show columns per table
                if is_spider and "tables" in schema:
                    tables_dict = schema.get("tables", {})
                    table_names = schema.get("table_names", [])
                    for tbl_name in table_names:
                        if tbl_name in tables_dict:
                            tbl_cols = tables_dict[tbl_name].get("columns", [])
                            parts.append(f"\nTable '{tbl_name}' Columns:")
                            for col in tbl_cols[:10]:  # Limit to first 10 columns per table
                                col_name = col.get("name", "")
                                col_type = col.get("type", "")
                                parts.append(f"  - {col_name} ({col_type})")
                            if len(tbl_cols) > 10:
                                parts.append(f"  ... and {len(tbl_cols) - 10} more columns")
                else:
                    # Single-table schema
                    parts.append("Columns:")
                    for col in columns:
                        col_name = col.get("name", "")
                        col_type = col.get("type", "")
                        parts.append(f"  - {col_name} ({col_type})")
        
        return "\n".join(parts)
    
    def _get_system_prompt(self, schema: Optional[Dict] = None) -> str:
        """Get system prompt for GPT-4."""
        # Detect WikiSQL_VALUE dataset
        is_wikisql = False
        if schema:
            is_wikisql = schema.get("database_name") == "wikisql_value" or \
                        any(col.get("db_name") for col in schema.get("columns", []))
        
        base_prompt = """You are a SQL expert. Generate SQL queries from natural language questions.

CRITICAL RULES:
1. Generate only SELECT queries (no INSERT, UPDATE, DELETE, DROP, etc.)
2. Use proper SQL syntax
3. ALWAYS use the EXACT table name(s) provided in the schema - NEVER use generic names like "table" or "Table"
4. Include WHERE clauses when filtering is needed
5. Use appropriate aggregation functions (COUNT, SUM, AVG, MAX, MIN) when needed
6. For multi-table queries, use JOIN clauses to connect related tables
7. Return only the SQL query, no explanations

Format your response as a plain SQL query."""
        
        if is_wikisql:
            base_prompt += """

CRITICAL FOR WIKISQL_VALUE DATASET:
- Use database column names (col0, col1, col2, etc.) NOT human-readable names
- The schema will show you the mapping between database names and human-readable names
- Always use the database column names (col0, col1, etc.) in your SQL queries
- Quote column names with double quotes: "col0", "col1", etc.
- Use single quotes for string values: 'value'"""
        else:
            base_prompt += """
5. Quote identifiers (table names, column names) with double quotes if they contain spaces or special characters"""
        
        return base_prompt
    
    def _get_few_shot_examples(self, schema: Optional[Dict] = None) -> str:
        """Get few-shot examples for prompting."""
        # Detect WikiSQL_VALUE dataset
        is_wikisql = False
        is_spider = False
        if schema:
            is_wikisql = schema.get("database_name") == "wikisql_value" or \
                        any(col.get("db_name") for col in schema.get("columns", []))
            is_spider = schema.get("database_name") and schema.get("database_name") != "wikisql_value" and \
                       ("tables" in schema or schema.get("metadata", {}).get("source") == "Spider")
        
        if is_spider:
            # Spider examples with actual table names
            examples = [
                {
                    "question": "How many employees are there?",
                    "sql": "SELECT COUNT(*) FROM employee"
                },
                {
                    "question": "What are the names of all students?",
                    "sql": "SELECT name FROM student"
                },
                {
                    "question": "Which city has the most flights?",
                    "sql": "SELECT T1.City FROM AIRPORTS AS T1 JOIN FLIGHTS AS T2 ON T1.AirportCode = T2.DestAirport GROUP BY T1.City ORDER BY COUNT(*) DESC LIMIT 1"
                }
            ]
            examples_text = "Examples:\n"
            for ex in examples:
                examples_text += f"Question: {ex['question']}\nSQL: {ex['sql']}\n\n"
            return examples_text
        elif is_wikisql:
            # WikiSQL_VALUE examples with database column names
            examples = [
                {
                    "question": "What position does the player who played for Duke play?",
                    "sql": "SELECT col3 FROM table_1_10015132_11 WHERE col5 = 'Duke'"
                },
                {
                    "question": "How many schools did player number 3 play at?",
                    "sql": "SELECT COUNT(col5) FROM table_1_10015132_11 WHERE col1 = '3'"
                },
                {
                    "question": "Who is the player that wears number 42?",
                    "sql": "SELECT col0 FROM table_1_10015132_11 WHERE col1 = '42'"
                }
            ]
        else:
            # Spider examples with schema column names
            examples = [
                {
                    "question": "What position does the player who played for Duke play?",
                    "sql": "SELECT Position FROM table_10015132_11 WHERE \"School/Club Team\" = 'Duke'"
                },
                {
                    "question": "How many schools did player number 3 play at?",
                    "sql": "SELECT COUNT(\"School/Club Team\") FROM table_10015132_11 WHERE \"No.\" = '3'"
                },
                {
                    "question": "Who is the player that wears number 42?",
                    "sql": "SELECT Player FROM table_10015132_11 WHERE \"No.\" = '42'"
                }
            ]
        
        formatted = []
        for ex in examples:
            formatted.append(f"Question: {ex['question']}")
            formatted.append(f"SQL: {ex['sql']}")
            formatted.append("")
        
        return "\n".join(formatted)
    
    def _clean_sql(self, sql: str) -> str:
        """
        Clean SQL string (remove markdown code blocks, etc.).
        
        Args:
            sql: Raw SQL string
            
        Returns:
            Cleaned SQL string
        """
        # Remove markdown code blocks
        if sql.startswith("```sql"):
            sql = sql.replace("```sql", "").replace("```", "").strip()
        elif sql.startswith("```"):
            sql = sql.replace("```", "").strip()
        
        # Remove leading/trailing whitespace
        sql = sql.strip()
        
        return sql
    
    def _fix_identifier_quoting(self, sql: str, schema: Dict) -> str:
        """
        Fix identifier quoting in generated SQL based on schema.
        
        Quotes column names and table names that contain special characters
        to ensure valid SQL syntax. Only quotes unquoted identifiers.
        
        Args:
            sql: Generated SQL string
            schema: Database schema dictionary
            
        Returns:
            SQL string with properly quoted identifiers
        """
        import re
        
        # Get schema identifiers
        table_name = schema.get("table_name") or schema.get("name", "")
        columns = schema.get("columns", [])
        column_names = [col.get("name", "") for col in columns]
        
        # Quote table name if needed (only if unquoted)
        if table_name and needs_quoting(table_name):
            quoted_table = quote_identifier(table_name)
            # Only replace if not already quoted
            # Check for unquoted table name (not inside quotes)
            pattern = re.compile(r'(?<!")' + re.escape(table_name) + r'(?!")', re.IGNORECASE)
            sql = pattern.sub(quoted_table, sql)
        
        # Quote column names if needed (only if unquoted)
        for col_name in column_names:
            if col_name and needs_quoting(col_name):
                quoted_col = quote_identifier(col_name)
                # Only replace unquoted column names
                # Pattern: not preceded by quote, column name, not followed by quote
                # Also avoid replacing inside string literals
                pattern = re.compile(
                    r'(?<!["\'])' + re.escape(col_name) + r'(?!["\'])',
                    re.IGNORECASE
                )
                
                # Replace only if not already quoted
                def replace_if_unquoted(match):
                    start = match.start()
                    end = match.end()
                    # Check if already quoted
                    if start > 0 and sql[start-1] == '"' and end < len(sql) and sql[end] == '"':
                        return match.group(0)  # Already quoted, don't change
                    return quoted_col
                
                sql = pattern.sub(replace_if_unquoted, sql)
        
        return sql
    
    def _fix_generic_table_name(self, sql: str, schema: Dict) -> str:
        """
        Fix generic 'table' references in generated SQL.
        
        This is a critical fix for Spider dataset where GPT-4o often generates
        'FROM table' instead of actual table names.
        
        Args:
            sql: Generated SQL string
            schema: Database schema dictionary
            
        Returns:
            SQL string with generic table names replaced
        """
        import re
        
        # Check if SQL contains generic table references
        # Match: FROM table, FROM "table", FROM 'table', FROM table_XXX (WikiSQL pattern)
        generic_patterns = [
            r'\bFROM\s+["\']?table["\']?\b',  # FROM table or FROM "table"
            r'\bFROM\s+table_\d+',  # FROM table_XXX (WikiSQL pattern used incorrectly)
        ]
        
        has_generic = any(re.search(pattern, sql, re.IGNORECASE) for pattern in generic_patterns)
        if not has_generic:
            return sql  # No generic table name found
        
        # Detect Spider multi-table schema
        is_spider = (schema.get("database_name") and schema.get("database_name") != "wikisql_value") or \
                   (schema.get("metadata", {}).get("source") == "Spider")
        
        if is_spider and "tables" in schema:
            # Multi-table schema (Spider) - try to infer which table to use
            table_names = schema.get("table_names", [])
            tables_dict = schema.get("tables", {})
            
            if table_names:
                # Try to infer table from column names mentioned in SQL
                sql_upper = sql.upper()
                matched_table = None
                
                # Check which table's columns are mentioned in the SQL
                for tbl_name in table_names:
                    if tbl_name in tables_dict:
                        table_cols = [col.get("name", "").upper() for col in tables_dict[tbl_name].get("columns", [])]
                        # If SQL mentions columns from this table, use it
                        if any(col in sql_upper for col in table_cols if col):
                            matched_table = tbl_name
                            break
                
                # Fallback to first table if no match found
                if not matched_table:
                    matched_table = table_names[0]
                
                # Replace generic table references (try all patterns)
                for pattern in generic_patterns:
                    sql = re.sub(
                        pattern,
                        f'FROM {matched_table}',
                        sql,
                        flags=re.IGNORECASE
                    )
                logger.info(f"Fixed generic 'table' -> '{matched_table}' (Spider multi-table)")
        else:
            # Single-table schema
            table_name = schema.get("table_name") or schema.get("name", "")
            if table_name and table_name != "table":
                for pattern in generic_patterns:
                    sql = re.sub(
                        pattern,
                        f'FROM {table_name}',
                        sql,
                        flags=re.IGNORECASE
                    )
                logger.debug(f"Fixed generic 'table' -> '{table_name}'")
        
        return sql
    
    def _fix_column_names(self, sql: str, schema: Dict, db_connection=None) -> str:
        """
        Fix column names in generated SQL to match actual database column names.
        
        CONSERVATIVE APPROACH: Only fixes columns when:
        1. Schema column name does NOT exist in database (case-insensitive)
        2. We find a high-confidence match using normalization
        3. The match is clearly better (e.g., "town" -> "Hometown" when "town" doesn't exist)
        
        This prevents breaking queries that already use correct column names.
        
        Args:
            sql: Generated SQL string
            schema: Database schema dictionary
            db_connection: Optional database connection to query actual column names
            
        Returns:
            SQL string with corrected column names
        """
        import re
        
        # Detect Spider dataset
        is_spider = (schema.get("database_name") and schema.get("database_name") != "wikisql_value") or \
                   (schema.get("metadata", {}).get("source") == "Spider")
        
        if not is_spider:
            return sql  # Only fix Spider for now
        
        # Get actual database column names if connection available
        db_column_map = {}
        if db_connection:
            try:
                db_column_map = self._get_database_column_names(schema, db_connection)
            except Exception as e:
                logger.debug(f"Could not get database column names: {e}")
                return sql  # Can't fix without DB info
        
        if not db_column_map:
            return sql  # No database column info available
        
        # Extract column names used in SQL (quoted, with table prefix)
        # Pattern: "column" or "table"."column"
        quoted_cols_pattern = re.compile(r'"([^"]+)"(?:\."([^"]+)")?')
        sql_column_refs = []
        for match in quoted_cols_pattern.finditer(sql):
            if match.group(2):  # "table"."column"
                sql_column_refs.append((match.group(1), match.group(2)))
            else:  # Just "column"
                sql_column_refs.append((None, match.group(1)))
        
        # Build column name mapping - ONLY for columns that don't exist in DB
        column_mapping = {}
        
        if "tables" in schema:
            tables_dict = schema.get("tables", {})
            
            # Process each column reference found in SQL
            for table_name_in_sql, col_name_in_sql in sql_column_refs:
                # Determine which table this column belongs to
                target_table = None
                if table_name_in_sql:
                    # Explicit table prefix in SQL
                    target_table = table_name_in_sql
                else:
                    # No table prefix - need to infer from schema
                    # Try to find table that has this column
                    for tbl_name, tbl_info in tables_dict.items():
                        for col in tbl_info.get("columns", []):
                            if col.get("name", "").lower() == col_name_in_sql.lower():
                                target_table = tbl_name
                                break
                        if target_table:
                            break
                
                if not target_table or target_table not in db_column_map:
                    continue
                
                db_cols = db_column_map[target_table]
                db_cols_lower = {col.lower(): col for col in db_cols}
                col_lower = col_name_in_sql.lower()
                
                # CONSERVATIVE CHECK 1: Does this column name exist in DB? (case-insensitive)
                if col_lower in db_cols_lower:
                    # Column exists - don't fix (it's correct)
                    continue
                
                # CONSERVATIVE CHECK 2: Find match using normalization (only if column doesn't exist)
                matched_col = None
                confidence = 0
                
                # Normalize the column name
                col_normalized = col_lower.replace("_", "").replace("-", "").replace(" ", "")
                
                # Strategy 1: Normalized exact match (very high confidence)
                db_cols_normalized = {}
                for col in db_cols:
                    normalized = col.lower().replace("_", "").replace("-", "").replace(" ", "")
                    if normalized == col_normalized and normalized not in db_cols_normalized:
                        db_cols_normalized[normalized] = col
                
                if col_normalized in db_cols_normalized:
                    matched_col = db_cols_normalized[col_normalized]
                    confidence = 0.95
                
                # Strategy 2: Column name is a subset of DB column (e.g., "town" -> "Hometown")
                # Only if Strategy 1 didn't find a match
                if not matched_col:
                    col_words = set(col_name_in_sql.lower().replace("_", " ").replace("-", " ").split())
                    for db_col in db_cols:
                        db_col_lower = db_col.lower()
                        db_col_normalized = db_col_lower.replace("_", "").replace("-", "").replace(" ", "")
                        db_col_words = set(db_col_lower.replace("_", " ").replace("-", " ").split())
                        
                        # Check if normalized column name is contained in DB normalized
                        # AND schema words are subset of DB words
                        if (col_normalized in db_col_normalized and 
                            len(col_normalized) < len(db_col_normalized) and
                            col_words and col_words.issubset(db_col_words)):
                            matched_col = db_col
                            confidence = 0.8
                            break
                
                # ULTRA-CONSERVATIVE: Only create mapping if:
                # 1. High confidence (>= 0.9)
                # 2. Column name is clearly wrong (doesn't exist in DB)
                # 3. Match is unambiguous (normalized exact match preferred)
                if matched_col and confidence >= 0.9:
                    # Only map the exact quoted format found in SQL
                    if table_name_in_sql:
                        column_mapping[f'"{table_name_in_sql}"."{col_name_in_sql}"'] = f'{target_table}.{matched_col}'
                    else:
                        column_mapping[f'"{col_name_in_sql}"'] = matched_col
                    logger.info(f"Column name fix: '{col_name_in_sql}' -> '{matched_col}' (confidence: {confidence:.2f}, table: {target_table})")
        
        # Apply column name replacements (ONLY quoted exact matches)
        if column_mapping:
            # Sort by length (longest first) to avoid partial replacements
            sorted_mappings = sorted(column_mapping.items(), key=lambda x: -len(x[0]))
            
            for schema_name, db_name in sorted_mappings:
                # Only replace exact quoted matches (safest)
                if schema_name.startswith('"'):
                    sql = sql.replace(schema_name, db_name)
        
        return sql
    
    def _get_database_column_names(self, schema: Dict, db_connection) -> Dict[str, List[str]]:
        """
        Get actual column names from database using PRAGMA table_info.
        
        Args:
            schema: Database schema dictionary
            db_connection: Database connection
            
        Returns:
            Dictionary mapping table names to lists of column names
        """
        column_map = {}
        
        if "tables" in schema:
            tables_dict = schema.get("tables", {})
            table_names = schema.get("table_names", [])
            
            for table_name in table_names:
                try:
                    cursor = db_connection.cursor()
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()
                    # SQLite PRAGMA returns: (cid, name, type, notnull, dflt_value, pk)
                    column_names = [col[1] for col in columns]
                    column_map[table_name] = column_names
                except Exception as e:
                    logger.debug(f"Could not get columns for table {table_name}: {e}")
                    continue
        
        return column_map
    
    def generate_structured(self, question: str, schema: Optional[Dict] = None) -> Dict:
        """
        Generate SQL in WikiSQL structured format.
        
        Args:
            question: Natural language question
            schema: Database schema dictionary
            
        Returns:
            SQL in WikiSQL format: {sel, conds, agg}
        """
        # Generate SQL string first
        sql_string = self.generate(question, schema)
        
        # Parse to structured format (simplified - would need proper parser)
        # For now, return a placeholder structure
        # In production, you'd parse the SQL string properly
        
        return {
            "sel": 0,  # Would need to parse SELECT clause
            "conds": [],  # Would need to parse WHERE clause
            "agg": 0  # Would need to detect aggregation
        }


if __name__ == "__main__":
    # Test the generator
    import sys
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)
    
    # Test generation
    generator = GPT4SQLGenerator()
    
    test_schema = {
        "table_name": "employees",
        "columns": [
            {"name": "id", "type": "INTEGER"},
            {"name": "name", "type": "TEXT"},
            {"name": "department", "type": "TEXT"}
        ]
    }
    
    question = "What are all the employee names?"
    sql = generator.generate(question, test_schema)
    
    print(f"Question: {question}")
    print(f"Generated SQL: {sql}")
