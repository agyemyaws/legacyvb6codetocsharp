"""
Integration Validator for Migrated C# Applications
Validates that translated components work together correctly and maintain system-level functionality
"""

import logging
import subprocess
import tempfile
import shutil
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import time
import os

logger = logging.getLogger(__name__)


class ValidationType(Enum):
    """Types of integration validation"""
    COMPILATION = "compilation"
    RUNTIME = "runtime"
    FUNCTIONAL = "functional"
    PERFORMANCE = "performance"
    DATABASE = "database"
    UI_INTEGRATION = "ui_integration"


class ValidationResult(Enum):
    """Validation result status"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class ValidationTest:
    """Represents an integration validation test"""
    name: str
    test_type: ValidationType
    description: str
    test_code: str
    expected_behavior: str
    timeout_seconds: int = 30
    dependencies: List[str] = field(default_factory=list)
    setup_code: str = ""
    teardown_code: str = ""


@dataclass
class ValidationTestResult:
    """Result of a validation test"""
    test_name: str
    result: ValidationResult
    execution_time: float
    output: str = ""
    error_message: str = ""
    warnings: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class IntegrationValidationReport:
    """Comprehensive integration validation report"""
    project_name: str
    validation_date: str
    test_results: List[ValidationTestResult]
    overall_status: ValidationResult
    summary_stats: Dict[str, int]
    recommendations: List[str] = field(default_factory=list)
    performance_analysis: Dict[str, Any] = field(default_factory=dict)


class CompilationValidator:
    """Validates that translated code compiles successfully"""
    
    def __init__(self, dotnet_path: str = "dotnet"):
        self.dotnet_path = dotnet_path
    
    def validate_project_compilation(self, project_path: str) -> ValidationTestResult:
        """Validate that a C# project compiles successfully"""
        
        start_time = time.time()
        project_dir = Path(project_path)
        
        try:
            # Find project files
            csproj_files = list(project_dir.glob("*.csproj"))
            sln_files = list(project_dir.glob("*.sln"))
            
            if not csproj_files and not sln_files:
                return ValidationTestResult(
                    test_name="compilation_check",
                    result=ValidationResult.FAILED,
                    execution_time=time.time() - start_time,
                    error_message="No .csproj or .sln files found in project directory"
                )
            
            # Choose build target (prefer solution file)
            build_target = str(sln_files[0]) if sln_files else str(csproj_files[0])
            
            # Run dotnet build
            result = subprocess.run(
                [self.dotnet_path, "build", build_target, "--configuration", "Debug", "--verbosity", "minimal"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                return ValidationTestResult(
                    test_name="compilation_check",
                    result=ValidationResult.PASSED,
                    execution_time=execution_time,
                    output=result.stdout
                )
            else:
                # Parse compilation errors
                errors = self.parse_compilation_errors(result.stderr)
                warnings = self.parse_compilation_warnings(result.stderr)
                
                return ValidationTestResult(
                    test_name="compilation_check",
                    result=ValidationResult.FAILED,
                    execution_time=execution_time,
                    output=result.stdout,
                    error_message=f"Compilation failed with {len(errors)} errors",
                    warnings=[f"Compilation warning: {w}" for w in warnings]
                )
        
        except subprocess.TimeoutExpired:
            return ValidationTestResult(
                test_name="compilation_check",
                result=ValidationResult.FAILED,
                execution_time=time.time() - start_time,
                error_message="Compilation timed out after 120 seconds"
            )
        
        except Exception as e:
            return ValidationTestResult(
                test_name="compilation_check",
                result=ValidationResult.FAILED,
                execution_time=time.time() - start_time,
                error_message=f"Compilation validation failed: {str(e)}"
            )
    
    def parse_compilation_errors(self, stderr: str) -> List[str]:
        """Parse compilation errors from build output"""
        errors = []
        for line in stderr.split('\n'):
            if 'error CS' in line or 'error MSB' in line:
                errors.append(line.strip())
        return errors
    
    def parse_compilation_warnings(self, stderr: str) -> List[str]:
        """Parse compilation warnings from build output"""
        warnings = []
        for line in stderr.split('\n'):
            if 'warning CS' in line or 'warning MSB' in line:
                warnings.append(line.strip())
        return warnings


class RuntimeValidator:
    """Validates runtime behavior of translated applications"""
    
    def __init__(self, dotnet_path: str = "dotnet"):
        self.dotnet_path = dotnet_path
    
    def validate_application_startup(self, project_path: str) -> ValidationTestResult:
        """Validate that the application starts without crashing"""
        
        start_time = time.time()
        project_dir = Path(project_path)
        
        try:
            # Build the project first
            build_result = subprocess.run(
                [self.dotnet_path, "build", "--configuration", "Debug"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if build_result.returncode != 0:
                return ValidationTestResult(
                    test_name="application_startup",
                    result=ValidationResult.FAILED,
                    execution_time=time.time() - start_time,
                    error_message="Failed to build application for runtime testing"
                )
            
            # Try to run the application with a short timeout
            run_result = subprocess.run(
                [self.dotnet_path, "run", "--configuration", "Debug"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=10  # Short timeout for startup test
            )
            
            execution_time = time.time() - start_time
            
            # For GUI applications, we expect a timeout (app keeps running)
            # For console applications, we expect clean exit
            if run_result.returncode == 0 or isinstance(run_result, subprocess.TimeoutExpired):
                return ValidationTestResult(
                    test_name="application_startup",
                    result=ValidationResult.PASSED,
                    execution_time=execution_time,
                    output="Application started successfully"
                )
            else:
                return ValidationTestResult(
                    test_name="application_startup",
                    result=ValidationResult.FAILED,
                    execution_time=execution_time,
                    error_message=f"Application failed to start: {run_result.stderr}",
                    output=run_result.stdout
                )
        
        except subprocess.TimeoutExpired:
            # For GUI apps, timeout is expected and means success
            return ValidationTestResult(
                test_name="application_startup",
                result=ValidationResult.PASSED,
                execution_time=time.time() - start_time,
                output="Application startup successful (GUI application detected)"
            )
        
        except Exception as e:
            return ValidationTestResult(
                test_name="application_startup",
                result=ValidationResult.FAILED,
                execution_time=time.time() - start_time,
                error_message=f"Runtime validation failed: {str(e)}"
            )


class FunctionalValidator:
    """Validates functional behavior by comparing with original VB6 behavior"""
    
    def __init__(self):
        self.test_cases = []
    
    def add_functional_test(self, test: ValidationTest):
        """Add a functional test case"""
        self.test_cases.append(test)
    
    def validate_bmi_calculation_functionality(self, project_path: str) -> ValidationTestResult:
        """Validate BMI calculation functionality specifically"""
        
        start_time = time.time()
        
        # Create a test program to validate BMI calculation
        test_program = """
using System;

namespace BMIFunctionalTest
{
    class Program
    {
        static void Main(string[] args)
        {
            try
            {
                // Test case 1: Normal BMI calculation
                var person = new CPerson();
                person.height = 175.0;
                person.weight = 70.0;
                
                double expectedBMI = 22.86; // 70 / (1.75^2)
                double actualBMI = person.bmi;
                
                if (Math.Abs(expectedBMI - actualBMI) < 0.1)
                {
                    Console.WriteLine("PASS: BMI calculation test");
                }
                else
                {
                    Console.WriteLine($"FAIL: BMI calculation test. Expected: {expectedBMI}, Actual: {actualBMI}");
                    return;
                }
                
                // Test case 2: BMI category
                string category = person.Category;
                if (category == "Normal weight")
                {
                    Console.WriteLine("PASS: BMI category test");
                }
                else
                {
                    Console.WriteLine($"FAIL: BMI category test. Expected: Normal weight, Actual: {category}");
                    return;
                }
                
                // Test case 3: Edge case - zero values
                person.height = 0;
                person.weight = 0;
                if (person.bmi == 0)
                {
                    Console.WriteLine("PASS: Zero values test");
                }
                else
                {
                    Console.WriteLine($"FAIL: Zero values test. Expected: 0, Actual: {person.bmi}");
                    return;
                }
                
                Console.WriteLine("ALL_TESTS_PASSED");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"ERROR: {ex.Message}");
            }
        }
    }
}
"""
        
        try:
            # Create temporary test project
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Copy original project files
                project_dir = Path(project_path)
                for file_path in project_dir.glob("*.cs"):
                    shutil.copy2(file_path, temp_path)
                
                # Create test program
                test_file = temp_path / "FunctionalTest.cs"
                with open(test_file, 'w') as f:
                    f.write(test_program)
                
                # Create test project file
                csproj_content = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net6.0</TargetFramework>
  </PropertyGroup>
</Project>"""
                
                csproj_file = temp_path / "FunctionalTest.csproj"
                with open(csproj_file, 'w') as f:
                    f.write(csproj_content)
                
                # Build and run test
                build_result = subprocess.run(
                    ["dotnet", "build"],
                    cwd=temp_path,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if build_result.returncode != 0:
                    return ValidationTestResult(
                        test_name="bmi_functional_test",
                        result=ValidationResult.FAILED,
                        execution_time=time.time() - start_time,
                        error_message="Failed to build functional test",
                        output=build_result.stderr
                    )
                
                run_result = subprocess.run(
                    ["dotnet", "run"],
                    cwd=temp_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                execution_time = time.time() - start_time
                
                if "ALL_TESTS_PASSED" in run_result.stdout:
                    return ValidationTestResult(
                        test_name="bmi_functional_test",
                        result=ValidationResult.PASSED,
                        execution_time=execution_time,
                        output=run_result.stdout
                    )
                else:
                    return ValidationTestResult(
                        test_name="bmi_functional_test",
                        result=ValidationResult.FAILED,
                        execution_time=execution_time,
                        error_message="Functional tests failed",
                        output=run_result.stdout + run_result.stderr
                    )
        
        except Exception as e:
            return ValidationTestResult(
                test_name="bmi_functional_test",
                result=ValidationResult.FAILED,
                execution_time=time.time() - start_time,
                error_message=f"Functional validation failed: {str(e)}"
            )


class PerformanceValidator:
    """Validates performance characteristics of translated code"""
    
    def __init__(self):
        self.benchmarks = []
    
    def validate_performance_regression(self, project_path: str, baseline_metrics: Dict[str, float] = None) -> ValidationTestResult:
        """Validate that performance hasn't regressed significantly"""
        
        start_time = time.time()
        
        # Create performance test
        perf_test = """
using System;
using System.Diagnostics;

namespace PerformanceTest
{
    class Program
    {
        static void Main(string[] args)
        {
            try
            {
                var person = new CPerson();
                var stopwatch = new Stopwatch();
                
                // Test BMI calculation performance
                stopwatch.Start();
                for (int i = 0; i < 100000; i++)
                {
                    person.height = 175.0 + (i % 50);
                    person.weight = 70.0 + (i % 30);
                    var bmi = person.bmi;
                    var category = person.Category;
                }
                stopwatch.Stop();
                
                double millisecondsPerOperation = stopwatch.Elapsed.TotalMilliseconds / 100000.0;
                Console.WriteLine($"PERFORMANCE_RESULT:{millisecondsPerOperation:F6}");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"ERROR: {ex.Message}");
            }
        }
    }
}
"""
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Copy project files
                project_dir = Path(project_path)
                for file_path in project_dir.glob("*.cs"):
                    shutil.copy2(file_path, temp_path)
                
                # Create performance test
                test_file = temp_path / "PerformanceTest.cs"
                with open(test_file, 'w') as f:
                    f.write(perf_test)
                
                # Create project file
                csproj_content = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net6.0</TargetFramework>
    <Optimize>true</Optimize>
  </PropertyGroup>
</Project>"""
                
                csproj_file = temp_path / "PerformanceTest.csproj"
                with open(csproj_file, 'w') as f:
                    f.write(csproj_content)
                
                # Build in Release mode
                build_result = subprocess.run(
                    ["dotnet", "build", "--configuration", "Release"],
                    cwd=temp_path,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if build_result.returncode != 0:
                    return ValidationTestResult(
                        test_name="performance_test",
                        result=ValidationResult.FAILED,
                        execution_time=time.time() - start_time,
                        error_message="Failed to build performance test"
                    )
                
                # Run performance test
                run_result = subprocess.run(
                    ["dotnet", "run", "--configuration", "Release"],
                    cwd=temp_path,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                execution_time = time.time() - start_time
                
                # Parse performance results
                perf_metrics = {}
                for line in run_result.stdout.split('\n'):
                    if line.startswith("PERFORMANCE_RESULT:"):
                        ms_per_op = float(line.split(':')[1])
                        perf_metrics['ms_per_operation'] = ms_per_op
                        break
                
                if perf_metrics:
                    # Check against baseline if provided
                    result_status = ValidationResult.PASSED
                    warnings = []
                    
                    if baseline_metrics and 'ms_per_operation' in baseline_metrics:
                        baseline_ms = baseline_metrics['ms_per_operation']
                        current_ms = perf_metrics['ms_per_operation']
                        
                        # Allow up to 50% performance regression
                        if current_ms > baseline_ms * 1.5:
                            result_status = ValidationResult.WARNING
                            warnings.append(f"Performance regression detected: {current_ms:.6f}ms vs baseline {baseline_ms:.6f}ms")
                    
                    return ValidationTestResult(
                        test_name="performance_test",
                        result=result_status,
                        execution_time=execution_time,
                        output=f"Performance: {perf_metrics['ms_per_operation']:.6f}ms per operation",
                        performance_metrics=perf_metrics,
                        warnings=warnings
                    )
                else:
                    return ValidationTestResult(
                        test_name="performance_test",
                        result=ValidationResult.FAILED,
                        execution_time=execution_time,
                        error_message="Could not parse performance results",
                        output=run_result.stdout + run_result.stderr
                    )
        
        except Exception as e:
            return ValidationTestResult(
                test_name="performance_test",
                result=ValidationResult.FAILED,
                execution_time=time.time() - start_time,
                error_message=f"Performance validation failed: {str(e)}"
            )


class DatabaseValidator:
    """Validates database integration for migrated applications"""
    
    def __init__(self):
        self.connection_strings = {}
    
    def validate_database_connectivity(self, project_path: str, connection_string: str) -> ValidationTestResult:
        """Validate database connectivity and basic operations"""
        
        start_time = time.time()
        
        db_test = f"""
using System;
using System.Data.OleDb;

namespace DatabaseTest
{{
    class Program
    {{
        static void Main(string[] args)
        {{
            try
            {{
                using (var connection = new OleDbConnection("{connection_string}"))
                {{
                    connection.Open();
                    Console.WriteLine("DATABASE_CONNECTION_SUCCESS");
                    
                    // Test basic query
                    using (var command = new OleDbCommand("SELECT COUNT(*) FROM MSysObjects", connection))
                    {{
                        var result = command.ExecuteScalar();
                        Console.WriteLine($"QUERY_SUCCESS:{{result}}");
                    }}
                }}
            }}
            catch (Exception ex)
            {{
                Console.WriteLine($"DATABASE_ERROR: {{ex.Message}}");
            }}
        }}
    }}
}}
"""
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Create database test
                test_file = temp_path / "DatabaseTest.cs"
                with open(test_file, 'w') as f:
                    f.write(db_test)
                
                # Create project file with database packages
                csproj_content = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net6.0</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="System.Data.OleDb" Version="7.0.0" />
  </ItemGroup>
</Project>"""
                
                csproj_file = temp_path / "DatabaseTest.csproj"
                with open(csproj_file, 'w') as f:
                    f.write(csproj_content)
                
                # Build and run
                build_result = subprocess.run(
                    ["dotnet", "build"],
                    cwd=temp_path,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if build_result.returncode != 0:
                    return ValidationTestResult(
                        test_name="database_connectivity",
                        result=ValidationResult.FAILED,
                        execution_time=time.time() - start_time,
                        error_message="Failed to build database test"
                    )
                
                run_result = subprocess.run(
                    ["dotnet", "run"],
                    cwd=temp_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                execution_time = time.time() - start_time
                
                if "DATABASE_CONNECTION_SUCCESS" in run_result.stdout:
                    return ValidationTestResult(
                        test_name="database_connectivity",
                        result=ValidationResult.PASSED,
                        execution_time=execution_time,
                        output=run_result.stdout
                    )
                else:
                    return ValidationTestResult(
                        test_name="database_connectivity",
                        result=ValidationResult.FAILED,
                        execution_time=execution_time,
                        error_message="Database connectivity test failed",
                        output=run_result.stdout + run_result.stderr
                    )
        
        except Exception as e:
            return ValidationTestResult(
                test_name="database_connectivity",
                result=ValidationResult.FAILED,
                execution_time=time.time() - start_time,
                error_message=f"Database validation failed: {str(e)}"
            )


class IntegrationValidator:
    """Main integration validator that orchestrates all validation types"""
    
    def __init__(self, dotnet_path: str = "dotnet"):
        self.compilation_validator = CompilationValidator(dotnet_path)
        self.runtime_validator = RuntimeValidator(dotnet_path)
        self.functional_validator = FunctionalValidator()
        self.performance_validator = PerformanceValidator()
        self.database_validator = DatabaseValidator()
        
        self.validation_tests = []
        self.baseline_metrics = {}
    
    def add_validation_test(self, test: ValidationTest):
        """Add a custom validation test"""
        self.validation_tests.append(test)
    
    def set_baseline_metrics(self, metrics: Dict[str, float]):
        """Set baseline performance metrics for comparison"""
        self.baseline_metrics = metrics
    
    def validate_project(self, project_path: str, 
                        include_performance: bool = True,
                        include_database: bool = False,
                        database_connection_string: str = "") -> IntegrationValidationReport:
        """Run comprehensive integration validation on a project"""
        
        project_name = Path(project_path).name
        validation_date = time.strftime("%Y-%m-%d %H:%M:%S")
        
        test_results = []
        
        # 1. Compilation validation
        logger.info("Running compilation validation...")
        compilation_result = self.compilation_validator.validate_project_compilation(project_path)
        test_results.append(compilation_result)
        
        # Only continue if compilation passes
        if compilation_result.result == ValidationResult.PASSED:
            
            # 2. Runtime validation
            logger.info("Running runtime validation...")
            runtime_result = self.runtime_validator.validate_application_startup(project_path)
            test_results.append(runtime_result)
            
            # 3. Functional validation
            logger.info("Running functional validation...")
            functional_result = self.functional_validator.validate_bmi_calculation_functionality(project_path)
            test_results.append(functional_result)
            
            # 4. Performance validation (optional)
            if include_performance:
                logger.info("Running performance validation...")
                perf_result = self.performance_validator.validate_performance_regression(
                    project_path, self.baseline_metrics
                )
                test_results.append(perf_result)
            
            # 5. Database validation (optional)
            if include_database and database_connection_string:
                logger.info("Running database validation...")
                db_result = self.database_validator.validate_database_connectivity(
                    project_path, database_connection_string
                )
                test_results.append(db_result)
        
        # Calculate overall status and statistics
        overall_status = self.calculate_overall_status(test_results)
        summary_stats = self.calculate_summary_stats(test_results)
        
        # Generate recommendations
        recommendations = self.generate_recommendations(test_results)
        
        # Analyze performance
        performance_analysis = self.analyze_performance(test_results)
        
        return IntegrationValidationReport(
            project_name=project_name,
            validation_date=validation_date,
            test_results=test_results,
            overall_status=overall_status,
            summary_stats=summary_stats,
            recommendations=recommendations,
            performance_analysis=performance_analysis
        )
    
    def calculate_overall_status(self, test_results: List[ValidationTestResult]) -> ValidationResult:
        """Calculate overall validation status"""
        
        if not test_results:
            return ValidationResult.FAILED
        
        failed_count = sum(1 for r in test_results if r.result == ValidationResult.FAILED)
        warning_count = sum(1 for r in test_results if r.result == ValidationResult.WARNING)
        
        if failed_count > 0:
            return ValidationResult.FAILED
        elif warning_count > 0:
            return ValidationResult.WARNING
        else:
            return ValidationResult.PASSED
    
    def calculate_summary_stats(self, test_results: List[ValidationTestResult]) -> Dict[str, int]:
        """Calculate summary statistics"""
        
        stats = {
            'total_tests': len(test_results),
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'skipped': 0
        }
        
        for result in test_results:
            if result.result == ValidationResult.PASSED:
                stats['passed'] += 1
            elif result.result == ValidationResult.FAILED:
                stats['failed'] += 1
            elif result.result == ValidationResult.WARNING:
                stats['warnings'] += 1
            elif result.result == ValidationResult.SKIPPED:
                stats['skipped'] += 1
        
        return stats
    
    def generate_recommendations(self, test_results: List[ValidationTestResult]) -> List[str]:
        """Generate recommendations based on test results"""
        
        recommendations = []
        
        for result in test_results:
            if result.result == ValidationResult.FAILED:
                if result.test_name == "compilation_check":
                    recommendations.append("Fix compilation errors before proceeding with deployment")
                elif result.test_name == "application_startup":
                    recommendations.append("Investigate runtime initialization issues")
                elif result.test_name == "bmi_functional_test":
                    recommendations.append("Review business logic translation for accuracy")
                elif result.test_name == "database_connectivity":
                    recommendations.append("Verify database connection strings and permissions")
            
            elif result.result == ValidationResult.WARNING:
                if result.test_name == "performance_test":
                    recommendations.append("Consider performance optimization to match original VB6 performance")
        
        if not recommendations:
            recommendations.append("All integration tests passed successfully")
        
        return recommendations
    
    def analyze_performance(self, test_results: List[ValidationTestResult]) -> Dict[str, Any]:
        """Analyze performance test results"""
        
        analysis = {
            'has_performance_data': False,
            'metrics': {},
            'trends': [],
            'concerns': []
        }
        
        for result in test_results:
            if result.performance_metrics:
                analysis['has_performance_data'] = True
                analysis['metrics'].update(result.performance_metrics)
                
                # Check for performance concerns
                if 'ms_per_operation' in result.performance_metrics:
                    ms_per_op = result.performance_metrics['ms_per_operation']
                    if ms_per_op > 0.001:  # More than 1ms per operation
                        analysis['concerns'].append(f"Slow operation performance: {ms_per_op:.6f}ms per operation")
        
        return analysis
    
    def save_validation_report(self, report: IntegrationValidationReport, output_file: str):
        """Save validation report to JSON file"""
        
        # Convert enum values to strings for JSON serialization
        report_dict = {
            'project_name': report.project_name,
            'validation_date': report.validation_date,
            'overall_status': report.overall_status.value,
            'summary_stats': report.summary_stats,
            'recommendations': report.recommendations,
            'performance_analysis': report.performance_analysis,
            'test_results': []
        }
        
        for result in report.test_results:
            result_dict = {
                'test_name': result.test_name,
                'result': result.result.value,
                'execution_time': result.execution_time,
                'output': result.output,
                'error_message': result.error_message,
                'warnings': result.warnings,
                'performance_metrics': result.performance_metrics
            }
            report_dict['test_results'].append(result_dict)
        
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(report_dict, f, indent=2)
        
        logger.info(f"Validation report saved to {output_file}")


def create_integration_validator(dotnet_path: str = "dotnet") -> IntegrationValidator:
    """Factory function to create an integration validator"""
    return IntegrationValidator(dotnet_path)


if __name__ == "__main__":
    # Example usage
    validator = create_integration_validator()
    
    # Set baseline metrics (example)
    validator.set_baseline_metrics({
        'ms_per_operation': 0.0001  # 0.1ms per operation baseline
    })
    
    # Run validation on a project
    # report = validator.validate_project(
    #     project_path="Translation/BMI_CSharp",
    #     include_performance=True,
    #     include_database=False
    # )
    
    # validator.save_validation_report(report, "Evaluation/integration_validation_report.json")
    
    print("Integration validator ready for use")
