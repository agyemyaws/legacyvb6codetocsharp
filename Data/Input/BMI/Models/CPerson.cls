VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
  Persistable = 0  'NotPersistable
  DataBindingBehavior = 0  'vbNone
  DataSourceBehavior  = 0  'vbNone
  MTSTransactionMode  = 0  'NotAnMTSObject
END
Attribute VB_Name = "CPerson"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = True
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
' Class Module: CPerson
' Save this as CPerson.cls
' This class handles person data and BMI calculations

Option Explicit

' Private variables
Private m_Name As String
Private m_Height As Double
Private m_Weight As Double
Private m_BMI As Double
Private m_Category As String

' Properties
Public Property Let name(ByVal value As String)
    m_Name = value
End Property

Public Property Get name() As String
    name = m_Name
End Property

Public Property Let height(ByVal value As Double)
    If value > 0 Then
        m_Height = value
        CalculateBMI
    Else
        Err.Raise 1001, "CPerson", "Height must be positive"
    End If
End Property

Public Property Get height() As Double
    height = m_Height
End Property

Public Property Let weight(ByVal value As Double)
    If value > 0 Then
        m_Weight = value
        CalculateBMI
    Else
        Err.Raise 1002, "CPerson", "Weight must be positive"
    End If
End Property

Public Property Get weight() As Double
    weight = m_Weight
End Property

Public Property Get bmi() As Double
    bmi = m_BMI
End Property

Public Property Get Category() As String
    Category = m_Category
End Property

' Methods
Private Sub CalculateBMI()
    If m_Height > 0 And m_Weight > 0 Then
        m_BMI = m_Weight / ((m_Height / 100) ^ 2)
        m_Category = GetBMICategory(m_BMI)
    End If
End Sub

Private Function GetBMICategory(bmi As Double) As String
    Select Case bmi
        Case Is < 18.5
            GetBMICategory = "Underweight"
        Case 18.5 To 24.99
            GetBMICategory = "Normal weight"
        Case 25 To 29.99
            GetBMICategory = "Overweight"
        Case Else
            GetBMICategory = "Obese"
    End Select
End Function

Public Function GetBMIReport() As String
    Dim report As String
    
    If m_BMI > 0 Then
        report = "BMI Report" & vbCrLf
        report = report & String(30, "-") & vbCrLf
        If Len(m_Name) > 0 Then
            report = report & "Name: " & m_Name & vbCrLf
        End If
        report = report & "Height: " & Format(m_Height, "0.00") & " cm" & vbCrLf
        report = report & "Weight: " & Format(m_Weight, "0.00") & " kg" & vbCrLf
        report = report & "BMI: " & Format(m_BMI, "0.00") & vbCrLf
        report = report & "Category: " & m_Category & vbCrLf
        report = report & String(30, "-")
    Else
        report = "No BMI data available"
    End If
    
    GetBMIReport = report
End Function

' Initialize
Private Sub Class_Initialize()
    m_Name = ""
    m_Height = 0
    m_Weight = 0
    m_BMI = 0
    m_Category = ""
End Sub
