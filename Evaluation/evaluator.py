"""
Evaluation framework for assessing translation quality and performance.
Implements quantitative metrics and qualitative assessment capabilities.
"""

import logging
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class EvaluationMetric(Enum):
    """Evaluation metric types"""
    COMPILATION_SUCCESS = "compilation_success"
    FUNCTIONAL_EQUIVALENCE = "functional_equivalence"
    CODE_QUALITY = "code_quality"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"


@dataclass
class EvaluationResult:
    """Result of an evaluation operation"""
    metric: EvaluationMetric
    value: float
    threshold: float
    passed: bool
    details: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None


@dataclass
class ComprehensiveEvaluation:
    """Comprehensive evaluation results"""
    source_file: str
    target_file: str
    metrics: Dict[EvaluationMetric, EvaluationResult]
    overall_score: float
    status: str
    recommendations: List[str]


class TranslationEvaluator:
    """Evaluator for translation quality and performance"""
    
    def __init__(self, 
                 compilation_threshold: float = 0.90,
                 functional_threshold: float = 0.85,
                 quality_threshold: float = 0.70):
        """
        Initialize the evaluator
        
        Args:
            compilation_threshold: Minimum compilation success rate
            functional_threshold: Minimum functional equivalence score
            quality_threshold: Minimum code quality score
        """
        self.compilation_threshold = compilation_threshold
        self.functional_threshold = functional_threshold
        self.quality_threshold = quality_threshold
        
        logger.info("Initialized translation evaluator")
    
    def evaluate_translation(self, 
                           source_file: str, 
                           target_file: str,
                           original_code: str,
                           translated_code: str) -> ComprehensiveEvaluation:
        """
        Perform comprehensive evaluation of a translation
        
        Args:
            source_file: Path to source file
            target_file: Path to translated file
            original_code: Original source code
            translated_code: Translated target code
            
        Returns:
            ComprehensiveEvaluation with all metrics and recommendations
        """
        metrics = {}
        
        # Compilation success evaluation
        compilation_result = self._evaluate_compilation_success(target_file, translated_code)
        metrics[EvaluationMetric.COMPILATION_SUCCESS] = compilation_result
        
        # Functional equivalence evaluation
        functional_result = self._evaluate_functional_equivalence(original_code, translated_code)
        metrics[EvaluationMetric.FUNCTIONAL_EQUIVALENCE] = functional_result
        
        # Code quality evaluation
        quality_result = self._evaluate_code_quality(translated_code)
        metrics[EvaluationMetric.CODE_QUALITY] = quality_result
        
        # Performance evaluation
        performance_result = self._evaluate_performance(original_code, translated_code)
        metrics[EvaluationMetric.PERFORMANCE] = performance_result
        
        # Maintainability evaluation
        maintainability_result = self._evaluate_maintainability(translated_code)
        metrics[EvaluationMetric.MAINTAINABILITY] = maintainability_result
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(metrics)
        
        # Determine status
        status = self._determine_status(metrics, overall_score)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(metrics)
        
        return ComprehensiveEvaluation(
            source_file=source_file,
            target_file=target_file,
            metrics=metrics,
            overall_score=overall_score,
            status=status,
            recommendations=recommendations
        )
    
    def _evaluate_compilation_success(self, target_file: str, translated_code: str) -> EvaluationResult:
        """Evaluate compilation success of translated code"""
        try:
            # Basic C# syntax validation
            syntax_valid = self._validate_csharp_syntax(translated_code)
            
            # Try to compile if syntax is valid
            compilation_success = False
            if syntax_valid:
                compilation_success = self._attempt_compilation(target_file, translated_code)
            
            success_rate = 1.0 if compilation_success else 0.0
            
            return EvaluationResult(
                metric=EvaluationMetric.COMPILATION_SUCCESS,
                value=success_rate,
                threshold=self.compilation_threshold,
                passed=success_rate >= self.compilation_threshold,
                details={
                    'syntax_valid': syntax_valid,
                    'compilation_success': compilation_success
                }
            )
            
        except Exception as e:
            logger.error(f"Compilation evaluation failed: {e}")
            return EvaluationResult(
                metric=EvaluationMetric.COMPILATION_SUCCESS,
                value=0.0,
                threshold=self.compilation_threshold,
                passed=False,
                errors=[str(e)]
            )
    
    def _evaluate_functional_equivalence(self, original_code: str, translated_code: str) -> EvaluationResult:
        """Evaluate functional equivalence between original and translated code"""
        try:
            # Basic structural comparison
            structural_similarity = self._calculate_structural_similarity(original_code, translated_code)
            
            # Check for key functionality preservation
            functionality_preserved = self._check_functionality_preservation(original_code, translated_code)
            
            # Calculate overall equivalence score
            equivalence_score = (structural_similarity + functionality_preserved) / 2
            
            return EvaluationResult(
                metric=EvaluationMetric.FUNCTIONAL_EQUIVALENCE,
                value=equivalence_score,
                threshold=self.functional_threshold,
                passed=equivalence_score >= self.functional_threshold,
                details={
                    'structural_similarity': structural_similarity,
                    'functionality_preserved': functionality_preserved
                }
            )
            
        except Exception as e:
            logger.error(f"Functional equivalence evaluation failed: {e}")
            return EvaluationResult(
                metric=EvaluationMetric.FUNCTIONAL_EQUIVALENCE,
                value=0.0,
                threshold=self.functional_threshold,
                passed=False,
                errors=[str(e)]
            )
    
    def _evaluate_code_quality(self, translated_code: str) -> EvaluationResult:
        """Evaluate code quality metrics"""
        try:
            # Calculate various quality metrics
            metrics = self._calculate_quality_metrics(translated_code)
            
            # Calculate overall quality score
            quality_score = self._calculate_quality_score(metrics)
            
            return EvaluationResult(
                metric=EvaluationMetric.CODE_QUALITY,
                value=quality_score,
                threshold=self.quality_threshold,
                passed=quality_score >= self.quality_threshold,
                details=metrics
            )
            
        except Exception as e:
            logger.error(f"Code quality evaluation failed: {e}")
            return EvaluationResult(
                metric=EvaluationMetric.CODE_QUALITY,
                value=0.0,
                threshold=self.quality_threshold,
                passed=False,
                errors=[str(e)]
            )
    
    def _evaluate_performance(self, original_code: str, translated_code: str) -> EvaluationResult:
        """Evaluate performance characteristics"""
        try:
            # Basic performance metrics
            original_complexity = self._calculate_complexity(original_code)
            translated_complexity = self._calculate_complexity(translated_code)
            
            # Performance preservation score
            complexity_ratio = min(original_complexity, translated_complexity) / max(original_complexity, translated_complexity)
            
            return EvaluationResult(
                metric=EvaluationMetric.PERFORMANCE,
                value=complexity_ratio,
                threshold=0.8,  # 80% performance preservation
                passed=complexity_ratio >= 0.8,
                details={
                    'original_complexity': original_complexity,
                    'translated_complexity': translated_complexity,
                    'complexity_ratio': complexity_ratio
                }
            )
            
        except Exception as e:
            logger.error(f"Performance evaluation failed: {e}")
            return EvaluationResult(
                metric=EvaluationMetric.PERFORMANCE,
                value=0.0,
                threshold=0.8,
                passed=False,
                errors=[str(e)]
            )
    
    def _evaluate_maintainability(self, translated_code: str) -> EvaluationResult:
        """Evaluate code maintainability"""
        try:
            # Calculate maintainability metrics
            maintainability_score = self._calculate_maintainability_score(translated_code)
            
            return EvaluationResult(
                metric=EvaluationMetric.MAINTAINABILITY,
                value=maintainability_score,
                threshold=0.7,  # 70% maintainability threshold
                passed=maintainability_score >= 0.7,
                details={
                    'maintainability_score': maintainability_score
                }
            )
            
        except Exception as e:
            logger.error(f"Maintainability evaluation failed: {e}")
            return EvaluationResult(
                metric=EvaluationMetric.MAINTAINABILITY,
                value=0.0,
                threshold=0.7,
                passed=False,
                errors=[str(e)]
            )
    
    def _validate_csharp_syntax(self, code: str) -> bool:
        """Validate basic C# syntax"""
        # Check for essential C# elements
        required_elements = ['using', 'namespace', 'class', '{', '}']
        return all(element in code for element in required_elements)
    
    def _attempt_compilation(self, target_file: str, translated_code: str) -> bool:
        """Attempt to compile the translated code"""
        try:
            # Save code to temporary file
            temp_file = Path(target_file)
            temp_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(translated_code)
            
            # Try to compile with dotnet
            result = subprocess.run(
                ['dotnet', 'build', target_file],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.warning(f"Compilation attempt failed: {e}")
            return False
    
    def _calculate_structural_similarity(self, original_code: str, translated_code: str) -> float:
        """Calculate structural similarity between original and translated code"""
        # Simple structural comparison
        original_lines = len(original_code.split('\n'))
        translated_lines = len(translated_code.split('\n'))
        
        if original_lines == 0 or translated_lines == 0:
            return 0.0
        
        # Calculate similarity based on line count ratio
        ratio = min(original_lines, translated_lines) / max(original_lines, translated_lines)
        return ratio
    
    def _check_functionality_preservation(self, original_code: str, translated_code: str) -> float:
        """Check if key functionality is preserved"""
        # Look for key functionality indicators
        original_indicators = self._extract_functionality_indicators(original_code)
        translated_indicators = self._extract_functionality_indicators(translated_code)
        
        if not original_indicators:
            return 1.0  # No indicators to preserve
        
        preserved_count = sum(1 for indicator in original_indicators if indicator in translated_indicators)
        return preserved_count / len(original_indicators)
    
    def _extract_functionality_indicators(self, code: str) -> List[str]:
        """Extract functionality indicators from code"""
        indicators = []
        
        # Look for common functionality patterns
        patterns = [
            'function', 'sub', 'procedure', 'method',
            'if', 'else', 'for', 'while', 'do',
            'return', 'exit', 'continue', 'break'
        ]
        
        for pattern in patterns:
            if pattern in code.lower():
                indicators.append(pattern)
        
        return indicators
    
    def _calculate_quality_metrics(self, code: str) -> Dict[str, Any]:
        """Calculate comprehensive quality metrics"""
        lines = code.split('\n')
        
        return {
            'total_lines': len(lines),
            'non_empty_lines': len([line for line in lines if line.strip()]),
            'comment_lines': len([line for line in lines if line.strip().startswith('//')]),
            'average_line_length': sum(len(line) for line in lines) / len(lines) if lines else 0,
            'cyclomatic_complexity': self._calculate_cyclomatic_complexity(code),
            'comment_ratio': len([line for line in lines if line.strip().startswith('//')]) / len(lines) if lines else 0
        }
    
    def _calculate_quality_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall quality score from metrics"""
        # Weighted combination of quality factors
        weights = {
            'comment_ratio': 0.2,
            'cyclomatic_complexity': 0.3,
            'average_line_length': 0.2,
            'non_empty_lines': 0.3
        }
        
        score = 0.0
        
        # Comment ratio score (higher is better, up to 0.3)
        comment_score = min(metrics['comment_ratio'] * 3, 1.0)
        score += comment_score * weights['comment_ratio']
        
        # Cyclomatic complexity score (lower is better)
        complexity_score = max(0, 1 - metrics['cyclomatic_complexity'] / 10)
        score += complexity_score * weights['cyclomatic_complexity']
        
        # Average line length score (optimal around 80 characters)
        line_length_score = max(0, 1 - abs(metrics['average_line_length'] - 80) / 80)
        score += line_length_score * weights['average_line_length']
        
        # Non-empty lines score (higher is better)
        non_empty_score = min(metrics['non_empty_lines'] / 100, 1.0)
        score += non_empty_score * weights['non_empty_lines']
        
        return score
    
    def _calculate_cyclomatic_complexity(self, code: str) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1  # Base complexity
        
        # Count decision points
        decision_keywords = ['if', 'else', 'for', 'while', 'do', 'case', 'catch', '&&', '||']
        
        for keyword in decision_keywords:
            complexity += code.lower().count(keyword)
        
        return complexity
    
    def _calculate_complexity(self, code: str) -> int:
        """Calculate overall code complexity"""
        return self._calculate_cyclomatic_complexity(code)
    
    def _calculate_maintainability_score(self, code: str) -> float:
        """Calculate maintainability score"""
        metrics = self._calculate_quality_metrics(code)
        
        # Maintainability factors
        comment_ratio = metrics['comment_ratio']
        complexity = metrics['cyclomatic_complexity']
        line_length = metrics['average_line_length']
        
        # Calculate maintainability score
        score = 0.0
        
        # Comment ratio contribution (up to 0.4)
        score += min(comment_ratio * 2, 0.4)
        
        # Complexity contribution (up to 0.4)
        complexity_score = max(0, 0.4 - complexity * 0.02)
        score += complexity_score
        
        # Line length contribution (up to 0.2)
        length_score = max(0, 0.2 - abs(line_length - 80) * 0.002)
        score += length_score
        
        return min(score, 1.0)
    
    def _calculate_overall_score(self, metrics: Dict[EvaluationMetric, EvaluationResult]) -> float:
        """Calculate overall evaluation score"""
        weights = {
            EvaluationMetric.COMPILATION_SUCCESS: 0.3,
            EvaluationMetric.FUNCTIONAL_EQUIVALENCE: 0.3,
            EvaluationMetric.CODE_QUALITY: 0.2,
            EvaluationMetric.PERFORMANCE: 0.1,
            EvaluationMetric.MAINTAINABILITY: 0.1
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for metric, result in metrics.items():
            if metric in weights:
                total_score += result.value * weights[metric]
                total_weight += weights[metric]
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def _determine_status(self, metrics: Dict[EvaluationMetric, EvaluationResult], overall_score: float) -> str:
        """Determine overall evaluation status"""
        if overall_score >= 0.9:
            return "EXCELLENT"
        elif overall_score >= 0.8:
            return "GOOD"
        elif overall_score >= 0.7:
            return "ACCEPTABLE"
        elif overall_score >= 0.6:
            return "NEEDS_IMPROVEMENT"
        else:
            return "FAILED"
    
    def _generate_recommendations(self, metrics: Dict[EvaluationMetric, EvaluationResult]) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        for metric, result in metrics.items():
            if not result.passed:
                if metric == EvaluationMetric.COMPILATION_SUCCESS:
                    recommendations.append("Fix compilation errors in translated code")
                elif metric == EvaluationMetric.FUNCTIONAL_EQUIVALENCE:
                    recommendations.append("Improve functional equivalence between original and translated code")
                elif metric == EvaluationMetric.CODE_QUALITY:
                    recommendations.append("Improve code quality and reduce complexity")
                elif metric == EvaluationMetric.PERFORMANCE:
                    recommendations.append("Optimize performance characteristics")
                elif metric == EvaluationMetric.MAINTAINABILITY:
                    recommendations.append("Improve code maintainability and documentation")
        
        return recommendations


def create_evaluator(**kwargs) -> TranslationEvaluator:
    """Factory function to create evaluator"""
    return TranslationEvaluator(**kwargs)


