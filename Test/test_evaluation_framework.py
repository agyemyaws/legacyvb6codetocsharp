#!/usr/bin/env python3
"""
Test script for the optimized VB6 static analyzer
"""

import sys
import os
from pathlib import Path

# Add the Utils directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "Utils"))

from static_analyzer import VB6StaticAnalyzer, analyze_vb6_codebase

def create_test_vb6_files():
    """Create test VB6 files for testing"""
    test_dir = Path("test_vb6_code")
    test_dir.mkdir(exist_ok=True)
    
    # Test form file
    form_content = '''VERSION 5.00
Begin VB.Form frmMain
   Caption         =   "Test Form"
   ClientHeight    =   3000
   ClientWidth     =   4000
   LinkTopic       =   "Form1"
   ScaleHeight     =   3000
   ScaleWidth      =   4000
   StartUpPosition =   3  'Windows Default
   Begin VB.CommandButton cmdTest
      Caption         =   "Test Button"
      Height          =   375
      Left            =   1200
      TabIndex        =   0
      Top             =   1200
      Width           =   1215
   End
   Begin VB.TextBox txtInput
      Height          =   375
      Left            =   1200
      TabIndex        =   1
      Text            =   "Text1"
      Top             =   600
      Width           =   1215
   End
End
Attribute VB_Name = "frmMain"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False

Private Sub cmdTest_Click()
    Dim result As String
    result = txtInput.Text
    If Len(result) > 0 Then
        MsgBox "Hello " & result
    Else
        MsgBox "Please enter text"
    End If
End Sub

Private Sub Form_Load()
    txtInput.Text = "Default Text"
End Sub
'''
    
    with open(test_dir / "frmMain.frm", "w") as f:
        f.write(form_content)
    
    # Test class file
    class_content = '''VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "clsTest"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = True
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False

Private m_name As String
Private m_value As Integer

Public Property Get Name() As String
    Name = m_name
End Property

Public Property Let Name(ByVal newName As String)
    m_name = newName
End Property

Public Function Calculate(ByVal x As Integer, ByVal y As Integer) As Integer
    Dim result As Integer
    result = x + y
    If result > 100 Then
        result = 100
    End If
    Calculate = result
End Function

Private Sub Initialize()
    m_name = "Default"
    m_value = 0
End Sub
'''
    
    with open(test_dir / "clsTest.cls", "w") as f:
        f.write(class_content)
    
    # Test module file
    module_content = '''Attribute VB_Name = "modUtilities"

Public Function FormatText(ByVal text As String) As String
    If Len(text) = 0 Then
        FormatText = ""
        Exit Function
    End If
    
    FormatText = UCase(Trim(text))
End Function

Public Sub LogMessage(ByVal message As String)
    Debug.Print "LOG: " & message
End Sub

Public Function IsValid(ByVal value As Variant) As Boolean
    IsValid = Not IsNull(value) And Not IsEmpty(value)
End Function
'''
    
    with open(test_dir / "modUtilities.bas", "w") as f:
        f.write(module_content)
    
    return test_dir

def test_vb6_analyzer():
    """Test the VB6 static analyzer"""
    print("🧪 Testing VB6 Static Analyzer")
    print("=" * 50)
    
    # Create test files
    test_dir = create_test_vb6_files()
    print(f"✅ Created test VB6 files in {test_dir}")
    
    try:
        # Test the analyzer
        analyzer = VB6StaticAnalyzer()
        results = analyzer.analyze_codebase(str(test_dir))
        
        print(f"\n📊 Analysis Results:")
        print(f"   Files analyzed: {len(results)}")
        
        for file_path, analysis in results.items():
            file_name = Path(file_path).name
            print(f"\n📁 {file_name}:")
            print(f"   Module: {analysis.module_name}")
            print(f"   Type: {analysis.file_type}")
            print(f"   Lines: {analysis.lines_of_code}")
            print(f"   Complexity: {analysis.cyclomatic_complexity}")
            print(f"   Functions/Subs: {len(analysis.module_boundaries)}")
            print(f"   Patterns: {len(analysis.detected_patterns)}")
            
            if analysis.controls:
                print(f"   Controls: {len(analysis.controls)}")
            
            if analysis.properties:
                print(f"   Properties: {len(analysis.properties)}")
        
        # Test report generation
        print("\n📝 Generating analysis report...")
        report = analyzer.generate_analysis_report(results)
        print("✅ Report generated successfully")
        
        # Test JSON export
        print("\n💾 Testing JSON export...")
        json_path = test_dir / "test_analysis.json"
        analyzer.export_analysis_json(results, str(json_path))
        print(f"✅ JSON exported to {json_path}")
        
        # Test convenience function
        print("\n🚀 Testing convenience function...")
        results2 = analyze_vb6_codebase(str(test_dir), export_json=False)
        print(f"✅ Convenience function returned {len(results2)} results")
        
        print("\n🎉 All tests passed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup test files
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print(f"\n🧹 Cleaned up test directory: {test_dir}")

if __name__ == "__main__":
    test_vb6_analyzer()
