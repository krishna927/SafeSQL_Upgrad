"""LLaMA-3 SQL Generator for SafeSQL framework (Free/Open-Source Option).

This module implements SQL generation using free/open-source LLMs:
- Option 1: Groq API (FREE tier) with LLaMA-3-8B-Instruct
- Option 2: HuggingFace Transformers (local inference, requires GPU)

This serves as Model 2 in the research proposal.
"""

import os
import json
from typing import Dict, List, Optional
import logging
from pathlib import Path

try:
    from openai import OpenAI  # Groq uses OpenAI-compatible API
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

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
        load_dotenv(env_path)


class LLaMASQLGenerator(BaseModel):
    """LLaMA-3 based SQL generator using free APIs or local inference."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize LLaMA SQL generator.
        
        Args:
            config: Configuration dictionary with:
                - provider: "groq" (free API) or "huggingface" (local)
                - api_key: API key for Groq (or use GROQ_API_KEY env var)
                - model: Model name (default: "llama-3.1-8b-instant" for Groq)
                - model_path: HuggingFace model path (for local inference)
                - temperature: Sampling temperature (default: 0.0)
                - max_tokens: Maximum tokens (default: 512)
                - use_gpu: Whether to use GPU for local inference (default: True)
        """
        super().__init__(config)
        
        self.provider = self.config.get("provider", "groq").lower()
        self.temperature = self.config.get("temperature", 0.0)
        self.max_tokens = self.config.get("max_tokens", 512)
        
        if self.provider == "groq":
            self._init_groq()
        elif self.provider == "huggingface":
            self._init_huggingface()
        else:
            raise ValueError(f"Unknown provider: {self.provider}. Use 'groq' or 'huggingface'")
        
        logger.info(f"LLaMASQLGenerator initialized with provider: {self.provider}")
    
    def _init_groq(self):
        """Initialize Groq API client (FREE tier available)."""
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI library not installed. Install with: pip install openai>=1.12.0"
            )
        
        # Groq uses OpenAI-compatible API
        api_key = self.config.get("api_key") or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "Groq API key required. Set GROQ_API_KEY environment variable "
                "or pass api_key in config.\n"
                "Get free API key at: https://console.groq.com/"
            )
        
        # Groq API endpoint
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        self.model = self.config.get("model", "llama-3.1-8b-instant")
        logger.info(f"Using Groq API with model: {self.model}")
    
    def _init_huggingface(self):
        """Initialize HuggingFace transformers for local inference."""
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "Transformers library not installed. Install with: pip install transformers torch"
            )
        
        model_path = self.config.get("model_path", "meta-llama/Llama-3-8B-Instruct")
        use_gpu = self.config.get("use_gpu", True) and torch.cuda.is_available()
        
        logger.info(f"Loading HuggingFace model: {model_path}")
        logger.info(f"Using {'GPU' if use_gpu else 'CPU'}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16 if use_gpu else torch.float32,
            device_map="auto" if use_gpu else None,
            low_cpu_mem_usage=True
        )
        
        if not use_gpu:
            self.model = self.model.to("cpu")
        
        self.model.eval()
        logger.info("HuggingFace model loaded successfully")
    
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
            db_connection: Optional database connection (for future use)
            **kwargs: Additional generation parameters
            
        Returns:
            Generated SQL query string
        """
        # Build prompt with schema
        full_prompt = self._build_prompt(prompt, schema)
        
        # Generate SQL
        if self.provider == "groq":
            sql = self._generate_groq(full_prompt, max_tokens, temperature)
        else:  # huggingface
            sql = self._generate_huggingface(full_prompt, max_tokens, temperature)
        
        # Clean up SQL (remove markdown code blocks if present)
        sql = self._clean_sql(sql)
        
        # Fix generic table names (same fix as GPT-4)
        if schema:
            sql = self._fix_generic_table_name(sql, schema)
        
        # Apply guardrails if provided
        if guardrails:
            guardrails_result = guardrails.apply_guardrails(sql)
            if not guardrails_result.get("safe", True):
                logger.warning(f"Unsafe SQL detected by guardrails: {guardrails_result.get('violations', [])}")
        
        return sql.strip()
    
    def _clean_sql(self, sql: str) -> str:
        """Clean up SQL string (remove markdown code blocks)."""
        if sql.startswith("```sql"):
            sql = sql.replace("```sql", "").replace("```", "").strip()
        elif sql.startswith("```"):
            sql = sql.replace("```", "").strip()
        return sql.strip()
    
    def _fix_generic_table_name(self, sql: str, schema: Dict) -> str:
        """Fix generic 'table' references in generated SQL (same as GPT-4)."""
        import re
        
        generic_patterns = [
            r'\bFROM\s+["\']?table["\']?\b',
            r'\bFROM\s+table_\d+',
        ]
        
        has_generic = any(re.search(pattern, sql, re.IGNORECASE) for pattern in generic_patterns)
        if not has_generic:
            return sql
        
        is_spider = (schema.get("database_name") and schema.get("database_name") != "wikisql_value") or \
                   (schema.get("metadata", {}).get("source") == "Spider")
        
        if is_spider and "tables" in schema:
            table_names = schema.get("table_names", [])
            tables_dict = schema.get("tables", {})
            
            if table_names:
                sql_upper = sql.upper()
                matched_table = None
                
                for tbl_name in table_names:
                    if tbl_name in tables_dict:
                        table_cols = [col.get("name", "").upper() for col in tables_dict[tbl_name].get("columns", [])]
                        if any(col in sql_upper for col in table_cols if col):
                            matched_table = tbl_name
                            break
                
                if not matched_table:
                    matched_table = table_names[0]
                
                for pattern in generic_patterns:
                    sql = re.sub(pattern, f'FROM {matched_table}', sql, flags=re.IGNORECASE)
                logger.debug(f"Fixed generic 'table' -> '{matched_table}' (Spider)")
        else:
            table_name = schema.get("table_name") or schema.get("name", "")
            if table_name and table_name != "table":
                # WikiSQL_VALUE: Ensure table name has 'table_1_' prefix if needed
                is_wikisql = schema.get("database_name") == "wikisql_value"
                if is_wikisql and table_name.startswith('table_') and not table_name.startswith('table_1_'):
                    # Add '1_' prefix after 'table_'
                    table_name = 'table_1_' + table_name[6:]  # Remove 'table_' and add 'table_1_'
                
                # Check if SQL already contains the table name to avoid duplication
                # Also check for partial matches to avoid appending to existing table names
                sql_lower = sql.lower()
                table_name_lower = table_name.lower()
                
                # Check if table name (or a variant) is already in SQL
                if table_name_lower not in sql_lower and f"from {table_name_lower}" not in sql_lower:
                    for pattern in generic_patterns:
                        sql = re.sub(pattern, f'FROM {table_name}', sql, flags=re.IGNORECASE)
                    logger.debug(f"Fixed generic 'table' -> '{table_name}'")
        
        return sql
    
    def _build_prompt(self, question: str, schema: Optional[Dict] = None) -> str:
        """Build prompt with schema information."""
        prompt_parts = [
            "You are an expert SQL generator. Generate valid SQL queries from natural language questions.",
            "\nGiven the database schema:"
        ]
        
        # Detect WikiSQL_VALUE dataset
        is_wikisql = False
        if schema:
            is_wikisql = schema.get("database_name") == "wikisql_value" or \
                        any(col.get("db_name") for col in schema.get("columns", []))
        
        if schema:
            # Extract table information
            tables = schema.get("tables", [])
            if isinstance(tables, list) and tables:
                for table in tables:
                    table_name = table.get("table_name", table.get("name", "table"))
                    columns = table.get("columns", [])
                    if columns:
                        if is_wikisql:
                            # WikiSQL_VALUE: Show column mapping
                            col_info_parts = []
                            for col in columns:
                                db_name = col.get("db_name", f"col{col.get('index', 0)}")
                                human_name = col.get("name", "")
                                col_info_parts.append(f"{db_name} (represents: {human_name})")
                            col_info = ", ".join(col_info_parts)
                            prompt_parts.append(f"\nTable: {table_name}")
                            prompt_parts.append("IMPORTANT: Use database column names (col0, col1, etc.) in your SQL queries.")
                            prompt_parts.append(f"Columns: {col_info}")
                        else:
                            col_info = ", ".join([col.get("name", col) if isinstance(col, dict) else col for col in columns])
                            prompt_parts.append(f"\nTable: {table_name}")
                            prompt_parts.append(f"Columns: {col_info}")
            else:
                # Single table schema
                table_name = schema.get("table_name") or schema.get("name", "table")
                columns = schema.get("columns", schema.get("header", []))
                if columns:
                    if is_wikisql:
                        # WikiSQL_VALUE: Show column mapping
                        col_info_parts = []
                        for col in columns:
                            if isinstance(col, dict):
                                db_name = col.get("db_name", f"col{col.get('index', 0)}")
                                human_name = col.get("name", "")
                                col_info_parts.append(f"{db_name} (represents: {human_name})")
                            else:
                                col_info_parts.append(str(col))
                        col_info = ", ".join(col_info_parts)
                        prompt_parts.append(f"\nTable: {table_name}")
                        prompt_parts.append("IMPORTANT: Use database column names (col0, col1, etc.) in your SQL queries.")
                        prompt_parts.append(f"Columns: {col_info}")
                    else:
                        col_info = ", ".join([col.get("name", col) if isinstance(col, dict) else str(col) for col in columns])
                        prompt_parts.append(f"\nTable: {table_name}")
                        prompt_parts.append(f"Columns: {col_info}")
        
        if is_wikisql:
            prompt_parts.append("\nCRITICAL: Use database column names (col0, col1, col2, etc.) NOT human-readable names.")
            prompt_parts.append("Example: SELECT col0 FROM table_1_XXX WHERE col1 = 'value'")
        
        prompt_parts.append(f"\n\nQuestion: {question}")
        prompt_parts.append("\nGenerate SQL query (only SQL, no explanation):")
        
        return "\n".join(prompt_parts)
    
    def _generate_groq(self, prompt: str, max_tokens: Optional[int] = None, temperature: Optional[float] = None) -> str:
        """Generate SQL using Groq API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert SQL generator. Only output valid SQL queries, nothing else."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens or self.max_tokens,
            )
            
            sql = response.choices[0].message.content.strip()
            
            # Extract SQL if wrapped in markdown code blocks
            if sql.startswith("```sql"):
                sql = sql.replace("```sql", "").replace("```", "").strip()
            elif sql.startswith("```"):
                sql = sql.replace("```", "").strip()
            
            return sql
            
        except Exception as e:
            logger.error(f"Error generating SQL with Groq: {e}")
            raise
    
    def _generate_huggingface(self, prompt: str, max_tokens: Optional[int] = None, temperature: Optional[float] = None) -> str:
        """Generate SQL using HuggingFace transformers."""
        try:
            # Tokenize input
            inputs = self.tokenizer(prompt, return_tensors="pt")
            if torch.cuda.is_available():
                inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens or self.max_tokens,
                    temperature=temperature if temperature is not None else (self.temperature + 0.1) or 0.1,
                    do_sample=temperature > 0 if temperature is not None else self.temperature > 0,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                )
            
            # Decode output
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract SQL (remove prompt)
            sql = generated_text[len(prompt):].strip()
            
            # Extract SQL if wrapped in markdown code blocks
            if sql.startswith("```sql"):
                sql = sql.replace("```sql", "").replace("```", "").strip()
            elif sql.startswith("```"):
                sql = sql.replace("```", "").strip()
            
            return sql
            
        except Exception as e:
            logger.error(f"Error generating SQL with HuggingFace: {e}")
            raise
    
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
        if schemas is None:
            schemas = [None] * len(prompts)
        
        results = []
        for prompt, schema in zip(prompts, schemas):
            sql = self.generate(prompt, schema=schema, **kwargs)
            results.append(sql)
        
        return results
    
    def get_model_info(self) -> Dict:
        """Get model information."""
        info = {
            "model_type": "LLaMA-3",
            "provider": self.provider,
            "config": self.config
        }
        
        if self.provider == "groq":
            info["model"] = self.model
            info["api_type"] = "Groq API (Free Tier)"
        else:
            info["model_path"] = self.config.get("model_path", "meta-llama/Llama-3-8B-Instruct")
            info["api_type"] = "HuggingFace Transformers (Local)"
        
        return info
