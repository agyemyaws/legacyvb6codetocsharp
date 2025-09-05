using System;
using System.Collections.Generic;
using System.Data;
using System.Data.OleDb;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using System.Windows.Forms;

namespace BMI.Utilities
{
    /// <summary>
    /// Converted from VB6 standard module: modDatabase
    /// Handles all database operations for BMI data
    /// </summary>
    public static class DatabaseModule
    {
        #region Private Fields
        private static OleDbConnection dbConnection;
        private static string connectionString;
        #endregion

        #region Private Constants
        private const string DB_NAME = "BMI_Database.mdb";
        private const string TABLE_NAME = "tblBMIHistory";
        #endregion

        #region Public Methods
        
        public static bool InitializeDatabase()
        {
            try
            {
                string dbPath = Path.Combine(Application.StartupPath, DB_NAME);
                
                if (!DatabaseExists(dbPath))
                {
                    if (!CreateDatabase(dbPath))
                    {
                        return false;
                    }
                }
                
                connectionString = $"Provider=Microsoft.Jet.OLEDB.4.0;Data Source={dbPath};Persist Security Info=False";
                
                using (var connection = new OleDbConnection(connectionString))
                {
                    connection.Open();
                    CreateBMITable(connection);
                }
                
                return true;
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Database Error: {ex.Message}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return false;
            }
        }

        public static bool SaveBMIRecord(CPerson objPerson)
        {
            try
            {
                if (string.IsNullOrEmpty(connectionString))
                {
                    if (!InitializeDatabase())
                    {
                        return false;
                    }
                }

                using (var connection = new OleDbConnection(connectionString))
                {
                    connection.Open();
                    
                    string strSQL = $"INSERT INTO {TABLE_NAME} " +
                                   "(DateRecorded, PersonName, Height, Weight, BMI, Category) " +
                                   "VALUES (?, ?, ?, ?, ?, ?)";
                    
                    using (var cmd = new OleDbCommand(strSQL, connection))
                    {
                        cmd.Parameters.AddWithValue("@p1", DateTime.Now);
                        cmd.Parameters.AddWithValue("@p2", objPerson.Name ?? string.Empty);
                        cmd.Parameters.AddWithValue("@p3", objPerson.Height);
                        cmd.Parameters.AddWithValue("@p4", objPerson.Weight);
                        cmd.Parameters.AddWithValue("@p5", objPerson.BMI);
                        cmd.Parameters.AddWithValue("@p6", objPerson.Category ?? string.Empty);
                        
                        cmd.ExecuteNonQuery();
                    }
                }
                
                return true;
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error saving record: {ex.Message}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return false;
            }
        }

        public static DataTable GetAllBMIRecords()
        {
            try
            {
                if (string.IsNullOrEmpty(connectionString))
                {
                    if (!InitializeDatabase())
                    {
                        return null;
                    }
                }

                using (var connection = new OleDbConnection(connectionString))
                {
                    connection.Open();
                    
                    string strSQL = $"SELECT * FROM {TABLE_NAME} ORDER BY DateRecorded DESC";
                    
                    using (var adapter = new OleDbDataAdapter(strSQL, connection))
                    {
                        var dataTable = new DataTable();
                        adapter.Fill(dataTable);
                        return dataTable;
                    }
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error retrieving records: {ex.Message}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return null;
            }
        }

        public static DataTable GetPersonBMIRecords(string personName)
        {
            try
            {
                if (string.IsNullOrEmpty(connectionString))
                {
                    if (!InitializeDatabase())
                    {
                        return null;
                    }
                }

                using (var connection = new OleDbConnection(connectionString))
                {
                    connection.Open();
                    
                    string strSQL = $"SELECT * FROM {TABLE_NAME} WHERE PersonName = ? ORDER BY DateRecorded DESC";
                    
                    using (var cmd = new OleDbCommand(strSQL, connection))
                    {
                        cmd.Parameters.AddWithValue("@p1", personName ?? string.Empty);
                        
                        using (var adapter = new OleDbDataAdapter(cmd))
                        {
                            var dataTable = new DataTable();
                            adapter.Fill(dataTable);
                            return dataTable;
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error retrieving person records: {ex.Message}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return null;
            }
        }

        public static string GetPersonStats(string personName)
        {
            try
            {
                if (string.IsNullOrEmpty(connectionString))
                {
                    if (!InitializeDatabase())
                    {
                        return "Unable to connect to database";
                    }
                }

                using (var connection = new OleDbConnection(connectionString))
                {
                    connection.Open();
                    
                    string strSQL = $"SELECT COUNT(*) as RecordCount, " +
                                   "AVG(BMI) as AvgBMI, " +
                                   "MIN(BMI) as MinBMI, " +
                                   "MAX(BMI) as MaxBMI " +
                                   $"FROM {TABLE_NAME} " +
                                   "WHERE PersonName = ?";
                    
                    using (var cmd = new OleDbCommand(strSQL, connection))
                    {
                        cmd.Parameters.AddWithValue("@p1", personName ?? string.Empty);
                        
                        using (var reader = cmd.ExecuteReader())
                        {
                            if (reader.Read())
                            {
                                var recordCount = Convert.ToInt32(reader["RecordCount"]);
                                var stats = new StringBuilder();
                                
                                stats.AppendLine($"Statistics for {personName}");
                                stats.AppendLine(new string('-', 40));
                                stats.AppendLine($"Total Records: {recordCount}");
                                
                                if (recordCount > 0)
                                {
                                    var avgBMI = Convert.ToDouble(reader["AvgBMI"]);
                                    var minBMI = Convert.ToDouble(reader["MinBMI"]);
                                    var maxBMI = Convert.ToDouble(reader["MaxBMI"]);
                                    
                                    stats.AppendLine($"Average BMI: {avgBMI:F2}");
                                    stats.AppendLine($"Lowest BMI: {minBMI:F2}");
                                    stats.Append($"Highest BMI: {maxBMI:F2}");
                                }
                                
                                return stats.ToString();
                            }
                            else
                            {
                                return $"No records found for {personName}";
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                return $"Error getting statistics: {ex.Message}";
            }
        }

        public static void CloseDatabase()
        {
            try
            {
                dbConnection?.Close();
                dbConnection?.Dispose();
                dbConnection = null;
            }
            catch
            {
                // Suppress errors on cleanup
            }
        }

        public static bool DeleteOldRecords(int daysToKeep)
        {
            try
            {
                if (string.IsNullOrEmpty(connectionString))
                {
                    if (!InitializeDatabase())
                    {
                        return false;
                    }
                }

                using (var connection = new OleDbConnection(connectionString))
                {
                    connection.Open();
                    
                    string strSQL = $"DELETE FROM {TABLE_NAME} " +
                                   "WHERE DateRecorded < DateAdd('d', ?, Now())";
                    
                    using (var cmd = new OleDbCommand(strSQL, connection))
                    {
                        cmd.Parameters.AddWithValue("@p1", -daysToKeep);
                        
                        int recordsDeleted = cmd.ExecuteNonQuery();
                        
                        MessageBox.Show($"{recordsDeleted} old records deleted.", "Information", 
                                      MessageBoxButtons.OK, MessageBoxIcon.Information);
                    }
                }
                
                return true;
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error deleting records: {ex.Message}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return false;
            }
        }

        #endregion

        #region Private Methods

        private static bool DatabaseExists(string dbPath)
        {
            return File.Exists(dbPath);
        }

        private static bool CreateDatabase(string dbPath)
        {
            try
            {
                var catalog = Activator.CreateInstance(Type.GetTypeFromProgID("ADOX.Catalog"));
                var createMethod = catalog.GetType().GetMethod("Create");
                createMethod.Invoke(catalog, new object[] { $"Provider=Microsoft.Jet.OLEDB.4.0;Data Source={dbPath}" });
                
                System.Runtime.InteropServices.Marshal.ReleaseComObject(catalog);
                return true;
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error creating database: {ex.Message}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return false;
            }
        }

        private static void CreateBMITable(OleDbConnection connection)
        {
            try
            {
                string strSQL = $"CREATE TABLE {TABLE_NAME} (" +
                               "ID AUTOINCREMENT PRIMARY KEY, " +
                               "DateRecorded DATETIME, " +
                               "PersonName VARCHAR(100), " +
                               "Height DOUBLE, " +
                               "Weight DOUBLE, " +
                               "BMI DOUBLE, " +
                               "Category VARCHAR(50))";
                
                using (var cmd = new OleDbCommand(strSQL, connection))
                {
                    cmd.ExecuteNonQuery();
                }
            }
            catch
            {
                // Table might already exist, suppress error
            }
        }

        #endregion
    }
}