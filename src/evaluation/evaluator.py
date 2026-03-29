"""Evaluation module for SafeSQL framework.

Implements standard NL2SQL evaluation metrics:
- Execution Accuracy (EX): Compare execution results
- Exact Match (EM): Compare SQL strings
- Safety Metrics: Guardrails and verification effectiveness
"""

import sqlite3
import json
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import hashlib

from ..utils.logger import get_logger

logger = get_logger(__name__)


class SQLResultComparator:
    """Compares SQL execution results."""
    
    @staticmethod
    def normalize_result(result: List[Tuple]) -> List[Tuple]:
        """
        Normalize SQL result for comparison.
        
        Args:
            result: List of tuples from SQL execution
            
        Returns:
            Normalized result (sorted, normalized types)
        """
        # Convert to list of lists for easier manipulation
        normalized = []
        for row in result:
            normalized_row = []
            for val in row:
                # Normalize types
                if val is None:
                    normalized_row.append(None)
                elif isinstance(val, (int, float)):
                    normalized_row.append(float(val))
                elif isinstance(val, str):
                    normalized_row.append(val.strip().lower())
                else:
                    normalized_row.append(str(val).strip().lower())
            normalized.append(tuple(normalized_row))
        
        # Sort rows (order-insensitive comparison)
        normalized.sort()
        return normalized
    
    @staticmethod
    def compare_results(result1: List[Tuple], result2: List[Tuple]) -> bool:
        """
        Compare two SQL execution results.
        
        Args:
            result1: First result set
            result2: Second result set
            
        Returns:
            True if results match
        """
        norm1 = SQLResultComparator.normalize_result(result1)
        norm2 = SQLResultComparator.normalize_result(result2)
        
        if len(norm1) != len(norm2):
            return False
        
        return norm1 == norm2


class SQLExecutor:
    """Executes SQL queries and returns results."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize SQL executor.
        
        Args:
            db_path: Path to SQLite database (optional, creates in-memory if None)
        """
        self.db_path = db_path
        self.conn = None
    
    def __enter__(self):
        """Context manager entry."""
        if self.db_path:
            self.conn = sqlite3.connect(self.db_path)
        else:
            self.conn = sqlite3.connect(":memory:")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.conn:
            self.conn.close()
    
    def create_table_from_schema(self, table_name: str, schema: Dict, data: List[Dict]):
        """
        Create table from schema and insert data.
        
        Args:
            table_name: Name of table
            schema: Schema dictionary with columns
            data: List of row dictionaries
        """
        if not self.conn:
            raise RuntimeError("Database connection not established")
        
        # Build CREATE TABLE statement
        columns = []
        for col in schema.get("columns", []):
            col_name = col["name"]
            col_type = col.get("type", "TEXT")
            columns.append(f'"{col_name}" {col_type}')
        
        create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(columns)})'
        self.conn.execute(create_sql)
        
        # Insert data
        if data:
            col_names = [col["name"] for col in schema.get("columns", [])]
            placeholders = ", ".join(["?" for _ in col_names])
            quoted_cols = ", ".join([f'"{c}"' for c in col_names])
            insert_sql = f'INSERT INTO "{table_name}" ({quoted_cols}) VALUES ({placeholders})'
            
            for row in data:
                # Handle both dict and list formats
                if isinstance(row, dict):
                    values = [row.get(col["name"]) for col in schema.get("columns", [])]
                else:
                    # Assume list format - use index
                    values = [row[i] if i < len(row) else None for i in range(len(col_names))]
                self.conn.execute(insert_sql, values)
        
        self.conn.commit()
    
    def execute(self, sql: str) -> Tuple[bool, List[Tuple], Optional[str]]:
        """
        Execute SQL query.
        
        Args:
            sql: SQL query string
            
        Returns:
            Tuple of (success, results, error_message)
        """
        if not self.conn:
            raise RuntimeError("Database connection not established")
        
        try:
            cursor = self.conn.execute(sql)
            results = cursor.fetchall()
            return True, results, None
        except Exception as e:
            return False, [], str(e)


class SafeSQLEvaluator:
    """Evaluates SafeSQL framework performance."""
    
    def __init__(self):
        """Initialize evaluator."""
        self.comparator = SQLResultComparator()
        logger.info("SafeSQLEvaluator initialized")
    
    def evaluate_execution_accuracy(
        self,
        generated_sql: str,
        gold_sql: str,
        table_name: str,
        schema: Dict,
        table_data: List[Dict],
        db_connection: Optional[sqlite3.Connection] = None
    ) -> Dict:
        """
        Evaluate execution accuracy (EX).
        
        Args:
            generated_sql: Generated SQL query
            gold_sql: Gold standard SQL query
            table_name: Name of table
            schema: Table schema
            table_data: Table data
            db_connection: Optional existing database connection (for Spider datasets)
            
        Returns:
            Evaluation result dictionary
        """
        result = {
            "ex": 0.0,
            "gold_executable": False,
            "generated_executable": False,
            "gold_error": None,
            "generated_error": None,
            "gold_result_count": 0,
            "generated_result_count": 0,
            "results_match": False
        }
        
        # If db_connection provided, use it directly (Spider case)
        if db_connection:
            executor = SQLExecutor()
            executor.conn = db_connection
            try:
                # Execute gold SQL
                gold_success, gold_results, gold_error = executor.execute(gold_sql)
                result["gold_executable"] = gold_success
                result["gold_error"] = gold_error
                result["gold_result_count"] = len(gold_results) if gold_success else 0
                
                # Execute generated SQL
                gen_success, gen_results, gen_error = executor.execute(generated_sql)
                result["generated_executable"] = gen_success
                result["generated_error"] = gen_error
                result["generated_result_count"] = len(gen_results) if gen_success else 0
                
                # Compare results if both executable
                if gold_success and gen_success:
                    results_match = self.comparator.compare_results(gold_results, gen_results)
                    result["results_match"] = results_match
                    result["ex"] = 1.0 if results_match else 0.0
                else:
                    result["ex"] = 0.0
            finally:
                # Don't close the connection, it's managed externally
                executor.conn = None
        else:
            # Execute both queries (WikiSQL case - create in-memory table)
            with SQLExecutor() as executor:
                # Create table
                executor.create_table_from_schema(table_name, schema, table_data)
                
                # Execute gold SQL
                gold_success, gold_results, gold_error = executor.execute(gold_sql)
                result["gold_executable"] = gold_success
                result["gold_error"] = gold_error
                result["gold_result_count"] = len(gold_results) if gold_success else 0
                
                # Execute generated SQL
                gen_success, gen_results, gen_error = executor.execute(generated_sql)
                result["generated_executable"] = gen_success
                result["generated_error"] = gen_error
                result["generated_result_count"] = len(gen_results) if gen_success else 0
                
                # Compare results if both executable
                if gold_success and gen_success:
                    results_match = self.comparator.compare_results(gold_results, gen_results)
                    result["results_match"] = results_match
                    result["ex"] = 1.0 if results_match else 0.0
                else:
                    result["ex"] = 0.0
        
        return result
    
    def evaluate_exact_match(self, generated_sql: str, gold_sql: str) -> Dict:
        """
        Evaluate exact match (EM).
        
        Args:
            generated_sql: Generated SQL query
            gold_sql: Gold standard SQL query
            
        Returns:
            Evaluation result dictionary
        """
        # Normalize SQL for comparison
        gen_normalized = self._normalize_sql(generated_sql)
        gold_normalized = self._normalize_sql(gold_sql)
        
        exact_match = gen_normalized == gold_normalized
        
        return {
            "em": 1.0 if exact_match else 0.0,
            "exact_match": exact_match,
            "generated_normalized": gen_normalized,
            "gold_normalized": gold_normalized
        }
    
    def _normalize_sql(self, sql: str) -> str:
        """
        Normalize SQL for comparison.
        
        Args:
            sql: SQL query string
            
        Returns:
            Normalized SQL string
        """
        # Remove extra whitespace
        sql = " ".join(sql.split())
        
        # Convert to uppercase
        sql = sql.upper()
        
        # Remove trailing semicolons
        sql = sql.rstrip(";")
        
        return sql
    
    def evaluate_safety(
        self,
        guardrails_result: Dict,
        verification_result: Dict
    ) -> Dict:
        """
        Evaluate safety metrics.
        
        Args:
            guardrails_result: Result from guardrails layer
            verification_result: Result from verification layer
            
        Returns:
            Safety evaluation dictionary
        """
        return {
            "guardrails_passed": guardrails_result.get("safe", False),
            "verification_passed": verification_result.get("safe_to_execute", False),
            "guardrails_violations": len(guardrails_result.get("violations", [])),
            "verification_errors": len(verification_result.get("errors", [])),
            "both_layers_passed": (
                guardrails_result.get("safe", False) and
                verification_result.get("safe_to_execute", False)
            )
        }
    
    def evaluate_single_query(
        self,
        question: str,
        generated_sql: str,
        gold_sql: str,
        table_name: str,
        schema: Dict,
        table_data: List[Dict],
        guardrails_result: Optional[Dict] = None,
        verification_result: Optional[Dict] = None,
        db_connection: Optional[sqlite3.Connection] = None
    ) -> Dict:
        """
        Evaluate a single query with all metrics.
        
        Args:
            question: Natural language question
            generated_sql: Generated SQL query
            gold_sql: Gold standard SQL query
            table_name: Table name
            schema: Table schema
            table_data: Table data
            guardrails_result: Guardrails result (optional)
            verification_result: Verification result (optional)
            db_connection: Optional existing database connection (for Spider datasets)
            
        Returns:
            Complete evaluation dictionary
        """
        # Execution Accuracy
        ex_result = self.evaluate_execution_accuracy(
            generated_sql, gold_sql, table_name, schema, table_data, db_connection=db_connection
        )
        
        # Exact Match
        em_result = self.evaluate_exact_match(generated_sql, gold_sql)
        
        # Safety (if provided)
        safety_result = {}
        if guardrails_result and verification_result:
            safety_result = self.evaluate_safety(guardrails_result, verification_result)
        
        return {
            "question": question,
            "generated_sql": generated_sql,
            "gold_sql": gold_sql,
            "execution_accuracy": ex_result,
            "exact_match": em_result,
            "safety": safety_result,
            "ex": ex_result["ex"],
            "em": em_result["em"]
        }
