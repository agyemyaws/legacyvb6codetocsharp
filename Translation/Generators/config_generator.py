"""
Configuration Generator - Application Configuration

This module handles the creation of application configuration files for translated VB6 projects.
It converts VB6 settings and configurations to modern C# configuration patterns using
appsettings.json, app.config, and other configuration mechanisms.

Key responsibilities:
- Convert VB6 app settings to appsettings.json
- Generate connection strings for modern data access
- Create logging configuration
- Handle application-specific settings
- Generate environment-specific configurations
- Convert registry settings to configuration files
"""

import json
import logging
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from xml.dom import minidom

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))


class ConfigurationType(Enum):
    """Types of configuration files"""
    APP_SETTINGS_JSON = "appsettings.json"
    APP_CONFIG_XML = "app.config"
    WEB_CONFIG_XML = "web.config"
    USER_SECRETS = "secrets.json"


class LogLevel(Enum):
    """Logging levels"""
    TRACE = "Trace"
    DEBUG = "Debug"
    INFORMATION = "Information"
    WARNING = "Warning"
    ERROR = "Error"
    CRITICAL = "Critical"
    NONE = "None"


@dataclass
class ConnectionString:
    """Represents a database connection string"""
    name: str
    connection_string: str
    provider: Optional[str] = None
    description: Optional[str] = None


@dataclass
class AppSetting:
    """Represents an application setting"""
    key: str
    value: Union[str, int, bool, float]
    description: Optional[str] = None
    environment_specific: bool = False


@dataclass
class LoggingConfiguration:
    """Represents logging configuration"""
    default_level: LogLevel = LogLevel.INFORMATION
    console_enabled: bool = True
    file_enabled: bool = False
    file_path: Optional[str] = None
    category_levels: Dict[str, LogLevel] = field(default_factory=dict)


class ConfigGenerator:
    """
    Generates modern C# configuration files from VB6 settings.
    
    This is specialized for configuration conversion, focusing on translating
    VB6-style settings (registry, INI files, embedded constants) to modern
    .NET configuration patterns.
    """
    
    def __init__(self, project_name: str, output_path: Path):
        self.logger = logging.getLogger(__name__)
        self.project_name = project_name
        self.output_path = Path(output_path)
        
        # Configuration collections
        self.connection_strings: List[ConnectionString] = []
        self.app_settings: List[AppSetting] = []
        self.logging_config = LoggingConfiguration()
        self.custom_sections: Dict[str, Dict[str, Any]] = {}
        
        # Environment-specific settings
        self.environments = ["Development", "Staging", "Production"]
        self.environment_settings: Dict[str, List[AppSetting]] = {}
        
        for env in self.environments:
            self.environment_settings[env] = []
    
    def add_connection_string(self, name: str, connection_string: str, 
                            provider: str = None, description: str = None) -> None:
        """Add a database connection string"""
        
        conn_str = ConnectionString(
            name=name,
            connection_string=connection_string,
            provider=provider,
            description=description
        )
        
        self.connection_strings.append(conn_str)
        self.logger.debug(f"Added connection string: {name}")
    
    def add_app_setting(self, key: str, value: Union[str, int, bool, float], 
                       description: str = None, environment_specific: bool = False) -> None:
        """Add an application setting"""
        
        setting = AppSetting(
            key=key,
            value=value,
            description=description,
            environment_specific=environment_specific
        )
        
        self.app_settings.append(setting)
        self.logger.debug(f"Added app setting: {key} = {value}")
    
    def add_environment_setting(self, environment: str, key: str, 
                               value: Union[str, int, bool, float], 
                               description: str = None) -> None:
        """Add an environment-specific setting"""
        
        if environment not in self.environment_settings:
            self.environment_settings[environment] = []
        
        setting = AppSetting(
            key=key,
            value=value,
            description=description,
            environment_specific=True
        )
        
        self.environment_settings[environment].append(setting)
        self.logger.debug(f"Added {environment} setting: {key} = {value}")
    
    def configure_logging(self, default_level: LogLevel = LogLevel.INFORMATION,
                         console_enabled: bool = True, file_enabled: bool = False,
                         file_path: str = None) -> None:
        """Configure logging settings"""
        
        self.logging_config = LoggingConfiguration(
            default_level=default_level,
            console_enabled=console_enabled,
            file_enabled=file_enabled,
            file_path=file_path or f"logs/{self.project_name}.log"
        )
        
        # Add common category levels
        self.logging_config.category_levels = {
            "Microsoft": LogLevel.WARNING,
            "Microsoft.Hosting.Lifetime": LogLevel.INFORMATION,
            "System": LogLevel.WARNING,
            f"{self.project_name}": LogLevel.DEBUG
        }
    
    def add_custom_section(self, section_name: str, settings: Dict[str, Any]) -> None:
        """Add a custom configuration section"""
        
        self.custom_sections[section_name] = settings
        self.logger.debug(f"Added custom section: {section_name}")
    
    def convert_vb6_registry_settings(self, registry_settings: Dict[str, str]) -> None:
        """Convert VB6 registry settings to app settings"""
        
        for reg_key, reg_value in registry_settings.items():
            # Convert registry key to setting key
            setting_key = self._convert_registry_key_to_setting_key(reg_key)
            
            # Convert value
            converted_value = self._convert_registry_value(reg_value)
            
            self.add_app_setting(
                key=setting_key,
                value=converted_value,
                description=f"Converted from registry: {reg_key}"
            )
    
    def convert_vb6_ini_settings(self, ini_settings: Dict[str, Dict[str, str]]) -> None:
        """Convert VB6 INI file settings to app settings"""
        
        for section_name, section_settings in ini_settings.items():
            # Create custom section or flatten to app settings
            if len(section_settings) > 3:  # Use custom section for larger groups
                self.add_custom_section(section_name, section_settings)
            else:
                # Flatten to app settings with section prefix
                for key, value in section_settings.items():
                    setting_key = f"{section_name}:{key}"
                    converted_value = self._convert_ini_value(value)
                    
                    self.add_app_setting(
                        key=setting_key,
                        value=converted_value,
                        description=f"Converted from INI: [{section_name}] {key}"
                    )
    
    def convert_vb6_connection_strings(self, vb6_connections: Dict[str, str]) -> None:
        """Convert VB6 connection strings to modern format"""
        
        for conn_name, conn_string in vb6_connections.items():
            # Convert VB6 connection string to modern format
            modern_conn_string = self._modernize_connection_string(conn_string)
            
            self.add_connection_string(
                name=conn_name,
                connection_string=modern_conn_string,
                provider="Microsoft.Data.SqlClient",
                description=f"Converted from VB6: {conn_name}"
            )
    
    def generate_appsettings_json(self, environment: str = None) -> str:
        """Generate appsettings.json content"""
        
        config = {}
        
        # Connection strings
        if self.connection_strings:
            config["ConnectionStrings"] = {}
            for conn_str in self.connection_strings:
                config["ConnectionStrings"][conn_str.name] = conn_str.connection_string
        
        # Logging configuration
        config["Logging"] = {
            "LogLevel": {
                "Default": self.logging_config.default_level.value
            }
        }
        
        # Add category-specific log levels
        for category, level in self.logging_config.category_levels.items():
            config["Logging"]["LogLevel"][category] = level.value
        
        # Console logging
        if self.logging_config.console_enabled:
            config["Logging"]["Console"] = {
                "LogLevel": {
                    "Default": self.logging_config.default_level.value
                }
            }
        
        # File logging
        if self.logging_config.file_enabled:
            config["Logging"]["File"] = {
                "LogLevel": {
                    "Default": self.logging_config.default_level.value
                },
                "Path": self.logging_config.file_path
            }
        
        # Application settings
        if self.app_settings:
            for setting in self.app_settings:
                if not setting.environment_specific:
                    config[setting.key] = setting.value
        
        # Environment-specific settings
        if environment and environment in self.environment_settings:
            for setting in self.environment_settings[environment]:
                config[setting.key] = setting.value
        
        # Custom sections
        for section_name, section_data in self.custom_sections.items():
            config[section_name] = section_data
        
        # Application-specific settings
        config[self.project_name] = {
            "ApplicationName": self.project_name,
            "Version": "1.0.0",
            "Environment": environment or "Development"
        }
        
        return json.dumps(config, indent=2, ensure_ascii=False)
    
    def generate_app_config_xml(self) -> str:
        """Generate app.config XML content for .NET Framework projects"""
        
        # Create root configuration element
        configuration = ET.Element("configuration")
        
        # Add configSections if needed
        if self.custom_sections:
            config_sections = ET.SubElement(configuration, "configSections")
            for section_name in self.custom_sections.keys():
                section_elem = ET.SubElement(config_sections, "section")
                section_elem.set("name", section_name)
                section_elem.set("type", "System.Configuration.NameValueSectionHandler")
        
        # Connection strings
        if self.connection_strings:
            conn_strings_elem = ET.SubElement(configuration, "connectionStrings")
            for conn_str in self.connection_strings:
                add_elem = ET.SubElement(conn_strings_elem, "add")
                add_elem.set("name", conn_str.name)
                add_elem.set("connectionString", conn_str.connection_string)
                if conn_str.provider:
                    add_elem.set("providerName", conn_str.provider)
        
        # App settings
        if self.app_settings:
            app_settings_elem = ET.SubElement(configuration, "appSettings")
            for setting in self.app_settings:
                if not setting.environment_specific:
                    add_elem = ET.SubElement(app_settings_elem, "add")
                    add_elem.set("key", setting.key)
                    add_elem.set("value", str(setting.value))
        
        # Custom sections
        for section_name, section_data in self.custom_sections.items():
            section_elem = ET.SubElement(configuration, section_name)
            for key, value in section_data.items():
                add_elem = ET.SubElement(section_elem, "add")
                add_elem.set("key", key)
                add_elem.set("value", str(value))
        
        # System.web for web applications
        # (This would be added if the project is identified as a web application)
        
        # Runtime configuration
        runtime_elem = ET.SubElement(configuration, "runtime")
        assemblyBinding_elem = ET.SubElement(runtime_elem, "assemblyBinding")
        assemblyBinding_elem.set("xmlns", "urn:schemas-microsoft-com:asm.v1")
        
        # Convert to pretty-printed XML
        xml_str = ET.tostring(configuration, encoding='unicode')
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent="  ")[23:]  # Remove XML declaration
    
    def save_configuration_files(self) -> List[Path]:
        """Save all configuration files to disk"""
        
        saved_files = []
        
        # Ensure output directory exists
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate main appsettings.json
        appsettings_path = self.output_path / "appsettings.json"
        appsettings_content = self.generate_appsettings_json()
        
        with open(appsettings_path, 'w', encoding='utf-8') as f:
            f.write(appsettings_content)
        saved_files.append(appsettings_path)
        self.logger.info(f"Generated appsettings.json: {appsettings_path}")
        
        # Generate environment-specific appsettings files
        for environment in self.environments:
            if environment in self.environment_settings and self.environment_settings[environment]:
                env_appsettings_path = self.output_path / f"appsettings.{environment}.json"
                env_appsettings_content = self.generate_appsettings_json(environment)
                
                with open(env_appsettings_path, 'w', encoding='utf-8') as f:
                    f.write(env_appsettings_content)
                saved_files.append(env_appsettings_path)
                self.logger.info(f"Generated {environment} appsettings: {env_appsettings_path}")
        
        # Generate app.config for .NET Framework compatibility
        app_config_path = self.output_path / "app.config"
        app_config_content = self.generate_app_config_xml()
        
        with open(app_config_path, 'w', encoding='utf-8') as f:
            f.write(app_config_content)
        saved_files.append(app_config_path)
        self.logger.info(f"Generated app.config: {app_config_path}")
        
        return saved_files
    
    def generate_configuration_summary(self) -> str:
        """Generate a summary of the configuration for documentation"""
        
        summary_lines = [
            f"# Configuration Summary for {self.project_name}",
            "",
            "## Connection Strings",
        ]
        
        if self.connection_strings:
            for conn_str in self.connection_strings:
                summary_lines.append(f"- **{conn_str.name}**: {conn_str.description or 'Database connection'}")
        else:
            summary_lines.append("- No connection strings configured")
        
        summary_lines.extend([
            "",
            "## Application Settings",
        ])
        
        if self.app_settings:
            for setting in self.app_settings:
                if not setting.environment_specific:
                    desc = setting.description or "Application setting"
                    summary_lines.append(f"- **{setting.key}**: {desc}")
        else:
            summary_lines.append("- No application settings configured")
        
        summary_lines.extend([
            "",
            "## Environment-Specific Settings",
        ])
        
        for environment, settings in self.environment_settings.items():
            if settings:
                summary_lines.append(f"### {environment}")
                for setting in settings:
                    desc = setting.description or "Environment-specific setting"
                    summary_lines.append(f"- **{setting.key}**: {desc}")
        
        summary_lines.extend([
            "",
            "## Logging Configuration",
            f"- Default Level: {self.logging_config.default_level.value}",
            f"- Console Logging: {'Enabled' if self.logging_config.console_enabled else 'Disabled'}",
            f"- File Logging: {'Enabled' if self.logging_config.file_enabled else 'Disabled'}",
        ])
        
        if self.logging_config.file_enabled:
            summary_lines.append(f"- Log File Path: {self.logging_config.file_path}")
        
        if self.custom_sections:
            summary_lines.extend([
                "",
                "## Custom Configuration Sections",
            ])
            for section_name in self.custom_sections.keys():
                summary_lines.append(f"- **{section_name}**: Custom configuration section")
        
        return "\n".join(summary_lines)
    
    def _convert_registry_key_to_setting_key(self, registry_key: str) -> str:
        """Convert a registry key to a configuration setting key"""
        
        # Remove registry prefixes
        key = registry_key.replace("HKEY_CURRENT_USER\\", "")
        key = key.replace("HKEY_LOCAL_MACHINE\\", "")
        key = key.replace("Software\\", "")
        
        # Convert backslashes to colons for hierarchical settings
        key = key.replace("\\", ":")
        
        return key
    
    def _convert_registry_value(self, registry_value: str) -> Union[str, int, bool]:
        """Convert a registry value to appropriate type"""
        
        # Try to convert to appropriate type
        if registry_value.lower() in ("true", "1", "yes"):
            return True
        elif registry_value.lower() in ("false", "0", "no"):
            return False
        elif registry_value.isdigit():
            return int(registry_value)
        else:
            return registry_value
    
    def _convert_ini_value(self, ini_value: str) -> Union[str, int, bool, float]:
        """Convert an INI value to appropriate type"""
        
        # Try to convert to appropriate type
        if ini_value.lower() in ("true", "yes", "on", "1"):
            return True
        elif ini_value.lower() in ("false", "no", "off", "0"):
            return False
        elif ini_value.replace(".", "").isdigit():
            try:
                if "." in ini_value:
                    return float(ini_value)
                else:
                    return int(ini_value)
            except ValueError:
                return ini_value
        else:
            return ini_value
    
    def _modernize_connection_string(self, vb6_connection_string: str) -> str:
        """Convert VB6 connection string to modern format"""
        
        # Common VB6 to modern connection string conversions
        conversions = {
            "Provider=Microsoft.Jet.OLEDB.4.0": "Provider=Microsoft.ACE.OLEDB.12.0",
            "Provider=SQLOLEDB": "Data Source=",
            "Data Source=": "Server=",
            "Initial Catalog=": "Database=",
            "Integrated Security=SSPI": "Integrated Security=true",
            "Trusted_Connection=yes": "Integrated Security=true"
        }
        
        modern_string = vb6_connection_string
        for old_part, new_part in conversions.items():
            modern_string = modern_string.replace(old_part, new_part)
        
        return modern_string


def create_configuration_from_vb6_project(project_name: str, output_path: Path,
                                        vb6_settings: Dict[str, Any]) -> ConfigGenerator:
    """
    Factory function to create configuration from VB6 project settings
    
    Args:
        project_name: Name of the project
        output_path: Directory where config files will be created
        vb6_settings: Dictionary containing VB6 settings and configurations
        
    Returns:
        Configured ConfigGenerator instance
    """
    
    generator = ConfigGenerator(project_name, output_path)
    
    # Convert different types of VB6 settings
    if 'registry_settings' in vb6_settings:
        generator.convert_vb6_registry_settings(vb6_settings['registry_settings'])
    
    if 'ini_settings' in vb6_settings:
        generator.convert_vb6_ini_settings(vb6_settings['ini_settings'])
    
    if 'connection_strings' in vb6_settings:
        generator.convert_vb6_connection_strings(vb6_settings['connection_strings'])
    
    # Add common application settings
    generator.add_app_setting("ApplicationName", project_name)
    generator.add_app_setting("Version", "1.0.0")
    generator.add_app_setting("StartupMode", "WinForms")
    
    # Configure logging
    generator.configure_logging(
        default_level=LogLevel.INFORMATION,
        console_enabled=True,
        file_enabled=True
    )
    
    # Add environment-specific settings
    generator.add_environment_setting("Development", "DetailedErrors", True)
    generator.add_environment_setting("Development", "LogLevel", "Debug")
    generator.add_environment_setting("Production", "DetailedErrors", False)
    generator.add_environment_setting("Production", "LogLevel", "Warning")
    
    return generator


def main():
    """Test the ConfigGenerator"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Test configuration creation
    output_path = Path("./test_output")
    generator = ConfigGenerator("TestProject", output_path)
    
    # Add test connection string
    generator.add_connection_string(
        name="DefaultConnection",
        connection_string="Server=localhost;Database=TestDB;Integrated Security=true;",
        provider="Microsoft.Data.SqlClient",
        description="Main application database"
    )
    
    # Add test settings
    generator.add_app_setting("MaxRetries", 3, "Maximum number of retry attempts")
    generator.add_app_setting("EnableDebugMode", False, "Enable debug mode")
    generator.add_app_setting("ApplicationTitle", "Test Application", "Application display title")
    
    # Add environment-specific settings
    generator.add_environment_setting("Development", "ApiUrl", "https://dev-api.example.com")
    generator.add_environment_setting("Production", "ApiUrl", "https://api.example.com")
    
    # Configure logging
    generator.configure_logging(LogLevel.DEBUG, console_enabled=True, file_enabled=True)
    
    # Add custom section
    generator.add_custom_section("EmailSettings", {
        "SmtpServer": "smtp.example.com",
        "Port": 587,
        "EnableSsl": True,
        "Username": "noreply@example.com"
    })
    
    # Save configuration files
    saved_files = generator.save_configuration_files()
    print(f"Generated configuration files: {[str(f) for f in saved_files]}")
    
    # Generate summary
    summary_path = output_path / "ConfigurationSummary.md"
    summary_content = generator.generate_configuration_summary()
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(summary_content)
    
    print(f"Generated configuration summary: {summary_path}")


if __name__ == "__main__":
    main()
