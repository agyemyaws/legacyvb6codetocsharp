VERSION 5.00
Begin VB.Form mainfrm 
   Caption         =   "Form1"
   ClientHeight    =   4755
   ClientLeft      =   60
   ClientTop       =   405
   ClientWidth     =   11640
   LinkTopic       =   "Form1"
   ScaleHeight     =   4755
   ScaleWidth      =   11640
   StartUpPosition =   3  'Windows Default
End
Attribute VB_Name = "mainfrm"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' Updated Form1 code that uses the Class and Module with Database
' This version saves to Access database

Option Explicit

' Declare controls with WithEvents to handle events
Private WithEvents txtHeight As TextBox
Attribute txtHeight.VB_VarHelpID = -1
Private WithEvents txtWeight As TextBox
Attribute txtWeight.VB_VarHelpID = -1
Private WithEvents txtName As TextBox
Attribute txtName.VB_VarHelpID = -1
Private WithEvents cmdCalculate As CommandButton
Attribute cmdCalculate.VB_VarHelpID = -1
Private WithEvents cmdClear As CommandButton
Attribute cmdClear.VB_VarHelpID = -1
Private WithEvents cmdSave As CommandButton
Attribute cmdSave.VB_VarHelpID = -1
Private WithEvents cmdViewHistory As CommandButton
Attribute cmdViewHistory.VB_VarHelpID = -1
Private WithEvents cmdStats As CommandButton
Attribute cmdStats.VB_VarHelpID = -1
Private lblHeight As Label
Private lblWeight As Label
Private lblName As Label
Private lblResult As Label
Private lblIdealWeight As Label

' Declare an instance of our Person class
Private objPerson As CPerson

Private Sub Form_Load()
    ' Create an instance of the Person class
    Set objPerson = New CPerson
    
    ' Initialize database
    If Not InitializeDatabase() Then
        MsgBox "Failed to initialize database. Data will not be saved.", vbExclamation
    End If
    
    ' Set form properties
    Me.Caption = "BMI Calculator with Database"
    Me.Width = 7000
    Me.height = 6000
    
    ' Create Name Label
    Set lblName = Me.Controls.Add("VB.Label", "lblName")
    With lblName
        .Caption = "Name:"
        .Left = 500
        .Top = 300
        .Width = 1200
        .height = 300
        .Visible = True
    End With
    
    ' Create Name TextBox
    Set txtName = Me.Controls.Add("VB.TextBox", "txtName")
    With txtName
        .Left = 1800
        .Top = 300
        .Width = 3000
        .height = 300
        .Text = ""
        .Visible = True
    End With
    
    ' Create Height Label
    Set lblHeight = Me.Controls.Add("VB.Label", "lblHeight")
    With lblHeight
        .Caption = "Height (cm):"
        .Left = 500
        .Top = 800
        .Width = 1200
        .height = 300
        .Visible = True
    End With
    
    ' Create Height TextBox
    Set txtHeight = Me.Controls.Add("VB.TextBox", "txtHeight")
    With txtHeight
        .Left = 1800
        .Top = 800
        .Width = 2000
        .height = 300
        .Text = ""
        .Visible = True
    End With
    
    ' Create Weight Label
    Set lblWeight = Me.Controls.Add("VB.Label", "lblWeight")
    With lblWeight
        .Caption = "Weight (kg):"
        .Left = 500
        .Top = 1300
        .Width = 1200
        .height = 300
        .Visible = True
    End With
    
    ' Create Weight TextBox
    Set txtWeight = Me.Controls.Add("VB.TextBox", "txtWeight")
    With txtWeight
        .Left = 1800
        .Top = 1300
        .Width = 2000
        .height = 300
        .Text = ""
        .Visible = True
    End With
    
    ' Create Calculate Button
    Set cmdCalculate = Me.Controls.Add("VB.CommandButton", "cmdCalculate")
    With cmdCalculate
        .Caption = "Calculate BMI"
        .Left = 500
        .Top = 1900
        .Width = 1300
        .height = 400
        .Visible = True
    End With
    
    ' Create Clear Button
    Set cmdClear = Me.Controls.Add("VB.CommandButton", "cmdClear")
    With cmdClear
        .Caption = "Clear"
        .Left = 1900
        .Top = 1900
        .Width = 1300
        .height = 400
        .Visible = True
    End With
    
    ' Create Save Button
    Set cmdSave = Me.Controls.Add("VB.CommandButton", "cmdSave")
    With cmdSave
        .Caption = "Save to DB"
        .Left = 3300
        .Top = 1900
        .Width = 1300
        .height = 400
        .Visible = True
        .Enabled = False
    End With
    
    ' Create View History Button
    Set cmdViewHistory = Me.Controls.Add("VB.CommandButton", "cmdViewHistory")
    With cmdViewHistory
        .Caption = "View History"
        .Left = 4700
        .Top = 1900
        .Width = 1300
        .height = 400
        .Visible = True
    End With
    
    ' Create Stats Button
    Set cmdStats = Me.Controls.Add("VB.CommandButton", "cmdStats")
    With cmdStats
        .Caption = "Statistics"
        .Left = 2500
        .Top = 4400
        .Width = 1500
        .height = 400
        .Visible = True
    End With
    
    ' Create Result Label
    Set lblResult = Me.Controls.Add("VB.Label", "lblResult")
    With lblResult
        .Caption = ""
        .Left = 500
        .Top = 2500
        .Width = 5500
        .height = 1200
        .Visible = True
        .BackColor = &H80000005 ' White
        .BorderStyle = 1 ' Fixed Single
    End With
    
    ' Create Ideal Weight Label
    Set lblIdealWeight = Me.Controls.Add("VB.Label", "lblIdealWeight")
    With lblIdealWeight
        .Caption = ""
        .Left = 500
        .Top = 3800
        .Width = 5500
        .height = 300
        .Visible = True
        .Alignment = 2 ' Center
    End With
End Sub

Private Sub cmdCalculate_Click()
    ' Use the validation function from our module
    If Not IsValidNumber(txtHeight.Text) Or Not IsValidNumber(txtWeight.Text) Then
        lblResult.Caption = "Please enter valid positive numbers for height and weight"
        lblResult.ForeColor = vbRed
        cmdSave.Enabled = False
        Exit Sub
    End If
    
    ' Set person properties (this will automatically calculate BMI)
    On Error GoTo ErrorHandler
    
    objPerson.name = txtName.Text
    objPerson.height = CDbl(txtHeight.Text)
    objPerson.weight = CDbl(txtWeight.Text)
    
    ' Display the BMI report
    lblResult.Caption = objPerson.GetBMIReport
    lblResult.ForeColor = GetBMIColorCode(objPerson.bmi)
    
    ' Show ideal weight range using module function
    lblIdealWeight.Caption = "Ideal weight range for your height: " & _
                            GetIdealWeightRange(objPerson.height)
    lblIdealWeight.ForeColor = vbBlue
    
    ' Enable save button
    cmdSave.Enabled = True
    
    Exit Sub
    
ErrorHandler:
    lblResult.Caption = "Error: " & Err.Description
    lblResult.ForeColor = vbRed
    cmdSave.Enabled = False
End Sub

Private Sub cmdClear_Click()
    ' Use the module function to clear textboxes
    ClearTextBoxes Me
    
    ' Clear labels
    lblResult.Caption = ""
    lblIdealWeight.Caption = ""
    
    ' Reset the person object
    Set objPerson = New CPerson
    
    ' Disable save button
    cmdSave.Enabled = False
    
    ' Set focus to name field
    txtName.SetFocus
End Sub

Private Sub cmdSave_Click()
    ' Save to database using the module function
    If SaveBMIRecord(objPerson) Then
        MsgBox "BMI data saved to database successfully!", vbInformation
    Else
        MsgBox "Failed to save data to database.", vbExclamation
    End If
End Sub

Private Sub cmdViewHistory_Click()
    ' Create a simple form to view history
    Dim rs As ADODB.Recordset
    Dim msg As String
    Dim recordCount As Integer
    
    ' Get records for the current person if name is entered, otherwise get all
    If Len(Trim(txtName.Text)) > 0 Then
        Set rs = GetPersonBMIRecords(txtName.Text)
        msg = "BMI History for " & txtName.Text & vbCrLf
    Else
        Set rs = GetAllBMIRecords()
        msg = "All BMI Records" & vbCrLf
    End If
    
    msg = msg & String(60, "-") & vbCrLf
    
    If Not rs Is Nothing Then
        If Not rs.EOF Then
            recordCount = 0
            Do While Not rs.EOF And recordCount < 10 ' Show last 10 records
                msg = msg & Format(rs!DateRecorded, "yyyy-mm-dd hh:nn") & " | "
                msg = msg & rs!personName & " | "
                msg = msg & "H: " & rs!height & "cm | "
                msg = msg & "W: " & rs!weight & "kg | "
                msg = msg & "BMI: " & Format(rs!bmi, "0.00") & " | "
                msg = msg & rs!Category & vbCrLf
                rs.MoveNext
                recordCount = recordCount + 1
            Loop
            
            If Not rs.EOF Then
                msg = msg & vbCrLf & "(Showing last 10 records)"
            End If
        Else
            msg = msg & "No records found."
        End If
        rs.Close
        Set rs = Nothing
    Else
        msg = msg & "Unable to retrieve records."
    End If
    
    MsgBox msg, vbInformation, "BMI History"
End Sub

Private Sub cmdStats_Click()
    ' Show statistics for a person
    Dim personName As String
    Dim stats As String
    
    personName = InputBox("Enter name to view statistics (leave blank for current):", "View Statistics", txtName.Text)
    
    If Len(Trim(personName)) = 0 Then
        MsgBox "Please enter a name to view statistics.", vbExclamation
        Exit Sub
    End If
    
    stats = GetPersonStats(personName)
    MsgBox stats, vbInformation, "BMI Statistics"
End Sub

' Optional: Add Enter key support for textboxes
Private Sub txtName_KeyPress(KeyAscii As Integer)
    If KeyAscii = 13 Then ' Enter key
        txtHeight.SetFocus
    End If
End Sub

Private Sub txtHeight_KeyPress(KeyAscii As Integer)
    If KeyAscii = 13 Then ' Enter key
        txtWeight.SetFocus
    End If
End Sub

Private Sub txtWeight_KeyPress(KeyAscii As Integer)
    If KeyAscii = 13 Then ' Enter key
        cmdCalculate_Click
    End If
End Sub

Private Sub Form_Unload(Cancel As Integer)
    ' Clean up
    Set objPerson = Nothing
    
    ' Close database connection
    CloseDatabase
End Sub

