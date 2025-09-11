Attribute VB_Name = "modDatabase"
' Module: modDatabase
' Save this as modDatabase.bas
' Handles all database operations for BMI data

Option Explicit

' ADO Connection and Recordset objects
Private dbConnection As ADODB.Connection
Private dbRecordset As ADODB.Recordset

' Database constants
Private Const DB_NAME As String = "BMI_Database.mdb"
Private Const TABLE_NAME As String = "tblBMIHistory"

' Initialize database connection
Public Function InitializeDatabase() As Boolean
    On Error GoTo ErrorHandler
    
    Dim dbPath As String
    dbPath = App.Path & "\" & DB_NAME
    
    ' Check if database exists, if not create it
    If Not DatabaseExists(dbPath) Then
        If Not CreateDatabase(dbPath) Then
            InitializeDatabase = False
            Exit Function
        End If
    End If
    
    ' Create connection
    Set dbConnection = New ADODB.Connection
    
    ' Connection string for Access database
    dbConnection.ConnectionString = "Provider=Microsoft.Jet.OLEDB.4.0;" & _
                                   "Data Source=" & dbPath & ";" & _
                                   "Persist Security Info=False"
    
    ' Open connection
    dbConnection.Open
    
    ' Create table if it doesn't exist
    CreateBMITable
    
    InitializeDatabase = True
    Exit Function
    
ErrorHandler:
    MsgBox "Database Error: " & Err.Description, vbCritical
    InitializeDatabase = False
End Function

' Check if database file exists
Private Function DatabaseExists(dbPath As String) As Boolean
    DatabaseExists = (Dir(dbPath) <> "")
End Function

' Create new Access database
Private Function CreateDatabase(dbPath As String) As Boolean
    On Error GoTo ErrorHandler
    
    Dim catalog As Object
    Set catalog = CreateObject("ADOX.Catalog")
    
    ' Create new database
    catalog.Create "Provider=Microsoft.Jet.OLEDB.4.0;" & _
                   "Data Source=" & dbPath
    
    Set catalog = Nothing
    CreateDatabase = True
    Exit Function
    
ErrorHandler:
    MsgBox "Error creating database: " & Err.Description, vbCritical
    CreateDatabase = False
End Function

' Create BMI History table
Private Sub CreateBMITable()
    On Error Resume Next
    
    Dim strSQL As String
    
    ' SQL to create table
    strSQL = "CREATE TABLE " & TABLE_NAME & " (" & _
             "ID AUTOINCREMENT PRIMARY KEY, " & _
             "DateRecorded DATETIME, " & _
             "PersonName VARCHAR(100), " & _
             "Height DOUBLE, " & _
             "Weight DOUBLE, " & _
             "BMI DOUBLE, " & _
             "Category VARCHAR(50))"
    
    ' Execute SQL
    dbConnection.Execute strSQL
End Sub

' Save BMI record to database
Public Function SaveBMIRecord(objPerson As CPerson) As Boolean
    On Error GoTo ErrorHandler
    
    Dim strSQL As String
    Dim cmd As ADODB.Command
    
    ' Check if connection is open
    If dbConnection Is Nothing Then
        If Not InitializeDatabase() Then
            SaveBMIRecord = False
            Exit Function
        End If
    End If
    
    If dbConnection.State <> adStateOpen Then
        dbConnection.Open
    End If
    
    ' Create command object for parameterized query
    Set cmd = New ADODB.Command
    Set cmd.ActiveConnection = dbConnection
    
    ' SQL Insert statement with parameters
    strSQL = "INSERT INTO " & TABLE_NAME & " " & _
             "(DateRecorded, PersonName, Height, Weight, BMI, Category) " & _
             "VALUES (?, ?, ?, ?, ?, ?)"
    
    cmd.CommandText = strSQL
    cmd.CommandType = adCmdText
    
    ' Add parameters
    cmd.Parameters.Append cmd.CreateParameter("p1", adDate, adParamInput, , Now)
    cmd.Parameters.Append cmd.CreateParameter("p2", adVarChar, adParamInput, 100, objPerson.name)
    cmd.Parameters.Append cmd.CreateParameter("p3", adDouble, adParamInput, , objPerson.height)
    cmd.Parameters.Append cmd.CreateParameter("p4", adDouble, adParamInput, , objPerson.weight)
    cmd.Parameters.Append cmd.CreateParameter("p5", adDouble, adParamInput, , objPerson.bmi)
    cmd.Parameters.Append cmd.CreateParameter("p6", adVarChar, adParamInput, 50, objPerson.Category)
    
    ' Execute the command
    cmd.Execute
    
    Set cmd = Nothing
    SaveBMIRecord = True
    Exit Function
    
ErrorHandler:
    MsgBox "Error saving record: " & Err.Description, vbCritical
    SaveBMIRecord = False
End Function

' Get all BMI records
Public Function GetAllBMIRecords() As ADODB.Recordset
    On Error GoTo ErrorHandler
    
    Dim strSQL As String
    
    ' Check connection
    If dbConnection Is Nothing Then
        If Not InitializeDatabase() Then
            Set GetAllBMIRecords = Nothing
            Exit Function
        End If
    End If
    
    If dbConnection.State <> adStateOpen Then
        dbConnection.Open
    End If
    
    ' Create recordset
    Set dbRecordset = New ADODB.Recordset
    
    ' SQL to get all records
    strSQL = "SELECT * FROM " & TABLE_NAME & " ORDER BY DateRecorded DESC"
    
    ' Open recordset
    dbRecordset.Open strSQL, dbConnection, adOpenStatic, adLockReadOnly
    
    Set GetAllBMIRecords = dbRecordset
    Exit Function
    
ErrorHandler:
    MsgBox "Error retrieving records: " & Err.Description, vbCritical
    Set GetAllBMIRecords = Nothing
End Function

' Get records for a specific person
Public Function GetPersonBMIRecords(personName As String) As ADODB.Recordset
    On Error GoTo ErrorHandler
    
    Dim strSQL As String
    Dim cmd As ADODB.Command
    
    ' Check connection
    If dbConnection Is Nothing Then
        If Not InitializeDatabase() Then
            Set GetPersonBMIRecords = Nothing
            Exit Function
        End If
    End If
    
    If dbConnection.State <> adStateOpen Then
        dbConnection.Open
    End If
    
    ' Create command and recordset
    Set cmd = New ADODB.Command
    Set dbRecordset = New ADODB.Recordset
    
    Set cmd.ActiveConnection = dbConnection
    
    ' SQL with parameter
    strSQL = "SELECT * FROM " & TABLE_NAME & " WHERE PersonName = ? ORDER BY DateRecorded DESC"
    
    cmd.CommandText = strSQL
    cmd.CommandType = adCmdText
    cmd.Parameters.Append cmd.CreateParameter("p1", adVarChar, adParamInput, 100, personName)
    
    ' Open recordset
    dbRecordset.Open cmd, , adOpenStatic, adLockReadOnly
    
    Set GetPersonBMIRecords = dbRecordset
    Set cmd = Nothing
    Exit Function
    
ErrorHandler:
    MsgBox "Error retrieving person records: " & Err.Description, vbCritical
    Set GetPersonBMIRecords = Nothing
End Function

' Get BMI statistics for a person
Public Function GetPersonStats(personName As String) As String
    On Error GoTo ErrorHandler
    
    Dim strSQL As String
    Dim rs As ADODB.Recordset
    Dim stats As String
    
    ' Check connection
    If dbConnection Is Nothing Then
        If Not InitializeDatabase() Then
            GetPersonStats = "Unable to connect to database"
            Exit Function
        End If
    End If
    
    If dbConnection.State <> adStateOpen Then
        dbConnection.Open
    End If
    
    Set rs = New ADODB.Recordset
    
    ' SQL to get statistics
    strSQL = "SELECT COUNT(*) as RecordCount, " & _
             "AVG(BMI) as AvgBMI, " & _
             "MIN(BMI) as MinBMI, " & _
             "MAX(BMI) as MaxBMI " & _
             "FROM " & TABLE_NAME & " " & _
             "WHERE PersonName = '" & Replace(personName, "'", "''") & "'"
    
    rs.Open strSQL, dbConnection, adOpenStatic, adLockReadOnly
    
    If Not rs.EOF Then
        stats = "Statistics for " & personName & vbCrLf
        stats = stats & String(40, "-") & vbCrLf
        stats = stats & "Total Records: " & rs!recordCount & vbCrLf
        
        If rs!recordCount > 0 Then
            stats = stats & "Average BMI: " & Format(rs!AvgBMI, "0.00") & vbCrLf
            stats = stats & "Lowest BMI: " & Format(rs!MinBMI, "0.00") & vbCrLf
            stats = stats & "Highest BMI: " & Format(rs!MaxBMI, "0.00")
        End If
    Else
        stats = "No records found for " & personName
    End If
    
    rs.Close
    Set rs = Nothing
    
    GetPersonStats = stats
    Exit Function
    
ErrorHandler:
    GetPersonStats = "Error getting statistics: " & Err.Description
End Function

' Close database connection
Public Sub CloseDatabase()
    On Error Resume Next
    
    If Not dbRecordset Is Nothing Then
        If dbRecordset.State = adStateOpen Then
            dbRecordset.Close
        End If
        Set dbRecordset = Nothing
    End If
    
    If Not dbConnection Is Nothing Then
        If dbConnection.State = adStateOpen Then
            dbConnection.Close
        End If
        Set dbConnection = Nothing
    End If
End Sub

' Delete old records (optional cleanup function)
Public Function DeleteOldRecords(daysToKeep As Integer) As Boolean
    On Error GoTo ErrorHandler
    
    Dim strSQL As String
    Dim recordsDeleted As Long
    
    ' Check connection
    If dbConnection Is Nothing Then
        If Not InitializeDatabase() Then
            DeleteOldRecords = False
            Exit Function
        End If
    End If
    
    If dbConnection.State <> adStateOpen Then
        dbConnection.Open
    End If
    
    ' SQL to delete old records
    strSQL = "DELETE FROM " & TABLE_NAME & " " & _
             "WHERE DateRecorded < DateAdd('d', -" & daysToKeep & ", Now())"
    
    dbConnection.Execute strSQL, recordsDeleted
    
    MsgBox recordsDeleted & " old records deleted.", vbInformation
    
    DeleteOldRecords = True
    Exit Function
    
ErrorHandler:
    MsgBox "Error deleting records: " & Err.Description, vbCritical
    DeleteOldRecords = False
End Function

