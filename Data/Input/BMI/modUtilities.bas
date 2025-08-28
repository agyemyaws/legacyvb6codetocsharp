Attribute VB_Name = "modUtilities"
' Standard Module: modUtilities
' Save this as modUtilities.bas
' This module contains utility functions and global constants

Option Explicit

' Global Constants for BMI Categories
Public Const BMI_UNDERWEIGHT As Double = 18.5
Public Const BMI_NORMAL_MAX As Double = 25
Public Const BMI_OVERWEIGHT_MAX As Double = 30

' Global Constants for Ideal Weight Calculation
Public Const IDEAL_BMI_MIN As Double = 18.5
Public Const IDEAL_BMI_MAX As Double = 24.9

' Validation Functions
Public Function IsValidNumber(ByVal strInput As String) As Boolean
    On Error GoTo ErrorHandler
    
    If Len(Trim(strInput)) = 0 Then
        IsValidNumber = False
        Exit Function
    End If
    
    If IsNumeric(strInput) Then
        If CDbl(strInput) > 0 Then
            IsValidNumber = True
        Else
            IsValidNumber = False
        End If
    Else
        IsValidNumber = False
    End If
    
    Exit Function
    
ErrorHandler:
    IsValidNumber = False
End Function

' Calculate Ideal Weight Range
Public Function GetIdealWeightRange(ByVal heightCm As Double) As String
    Dim minWeight As Double
    Dim maxWeight As Double
    Dim heightM As Double
    
    If heightCm <= 0 Then
        GetIdealWeightRange = "Invalid height"
        Exit Function
    End If
    
    heightM = heightCm / 100
    minWeight = IDEAL_BMI_MIN * (heightM ^ 2)
    maxWeight = IDEAL_BMI_MAX * (heightM ^ 2)
    
    GetIdealWeightRange = Format(minWeight, "0.0") & " - " & Format(maxWeight, "0.0") & " kg"
End Function

' Convert between metric and imperial units
Public Function PoundsToKg(ByVal pounds As Double) As Double
    PoundsToKg = pounds * 0.453592
End Function

Public Function KgToPounds(ByVal kg As Double) As Double
    KgToPounds = kg * 2.20462
End Function

Public Function FeetInchesToCm(ByVal feet As Integer, ByVal inches As Double) As Double
    FeetInchesToCm = (feet * 12 + inches) * 2.54
End Function

Public Function CmToFeetInches(ByVal cm As Double) As String
    Dim totalInches As Double
    Dim feet As Integer
    Dim inches As Double
    
    totalInches = cm / 2.54
    feet = Int(totalInches / 12)
    inches = totalInches - (feet * 12)
    
    CmToFeetInches = feet & "' " & Format(inches, "0.0") & """"
End Function

' Format BMI with color code (for use with labels or rich text boxes)
Public Function GetBMIColorCode(ByVal bmi As Double) As Long
    Select Case bmi
        Case Is < BMI_UNDERWEIGHT
            GetBMIColorCode = vbBlue ' Underweight
        Case BMI_UNDERWEIGHT To BMI_NORMAL_MAX - 0.01
            GetBMIColorCode = vbGreen ' Normal
        Case BMI_NORMAL_MAX To BMI_OVERWEIGHT_MAX - 0.01
            GetBMIColorCode = RGB(255, 165, 0) ' Orange for Overweight
        Case Else
            GetBMIColorCode = vbRed ' Obese
    End Select
End Function

' Save BMI History to file
Public Sub SaveBMIToFile(ByVal name As String, ByVal height As Double, _
                        ByVal weight As Double, ByVal bmi As Double)
    Dim fileNum As Integer
    Dim filePath As String
    
    On Error GoTo ErrorHandler
    
    filePath = App.Path & "\BMI_History.txt"
    fileNum = FreeFile
    
    Open filePath For Append As #fileNum
    Print #fileNum, Now & vbTab & name & vbTab & height & vbTab & _
                    weight & vbTab & Format(bmi, "0.00")
    Close #fileNum
    
    Exit Sub
    
ErrorHandler:
    MsgBox "Error saving to file: " & Err.Description, vbExclamation
End Sub

' Clear all textboxes on a form
Public Sub ClearTextBoxes(frm As Form)
    Dim ctrl As Control
    
    For Each ctrl In frm.Controls
        If TypeOf ctrl Is TextBox Then
            ctrl.Text = ""
        End If
    Next ctrl
End Sub

