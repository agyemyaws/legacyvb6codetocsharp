using System;
using System.ComponentModel;
using System.Drawing;
using System.Windows.Forms;
using BMI.Models;
using BMI.Data;
using BMI.Utils;

namespace BMI.UI
{
    public partial class Mainfrm : Form
    {
        private Person objPerson;

        public Mainfrm()
        {
            InitializeComponent();
        }

        private void Mainfrm_Load(object sender, EventArgs e)
        {
            // Create an instance of the Person class
            objPerson = new Person();
            
            // Initialize database
            if (!DatabaseHelper.InitializeDatabase())
            {
                MessageBox.Show("Failed to initialize database. Data will not be saved.", "Warning", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
            }
            
            // Set form properties
            this.Text = "BMI Calculator with Database";
            this.Size = new Size(7000 / 15, 6000 / 15); // Convert VB6 twips to pixels
            
            // Disable save button initially
            cmdSave.Enabled = false;
            
            // Set focus to name field
            txtName.Focus();
        }

        private void cmdCalculate_Click(object sender, EventArgs e)
        {
            // Use the validation function from our module
            if (!ValidationHelper.IsValidNumber(txtHeight.Text) || !ValidationHelper.IsValidNumber(txtWeight.Text))
            {
                lblResult.Text = "Please enter valid positive numbers for height and weight";
                lblResult.ForeColor = Color.Red;
                cmdSave.Enabled = false;
                return;
            }
            
            // Set person properties (this will automatically calculate BMI)
            try
            {
                objPerson.Name = txtName.Text;
                objPerson.Height = Convert.ToDouble(txtHeight.Text);
                objPerson.Weight = Convert.ToDouble(txtWeight.Text);
                
                // Display the BMI report
                lblResult.Text = objPerson.GetBMIReport();
                lblResult.ForeColor = BMIHelper.GetBMIColorCode(objPerson.BMI);
                
                // Show ideal weight range using module function
                lblIdealWeight.Text = "Ideal weight range for your height: " + 
                                    BMIHelper.GetIdealWeightRange(objPerson.Height);
                lblIdealWeight.ForeColor = Color.Blue;
                
                // Enable save button
                cmdSave.Enabled = true;
            }
            catch (Exception ex)
            {
                lblResult.Text = "Error: " + ex.Message;
                lblResult.ForeColor = Color.Red;
                cmdSave.Enabled = false;
            }
        }

        private void cmdClear_Click(object sender, EventArgs e)
        {
            // Use the module function to clear textboxes
            FormHelper.ClearTextBoxes(this);
            
            // Clear labels
            lblResult.Text = "";
            lblIdealWeight.Text = "";
            
            // Reset the person object
            objPerson = new Person();
            
            // Disable save button
            cmdSave.Enabled = false;
            
            // Set focus to name field
            txtName.Focus();
        }

        private void cmdSave_Click(object sender, EventArgs e)
        {
            // Save to database using the module function
            if (DatabaseHelper.SaveBMIRecord(objPerson))
            {
                MessageBox.Show("BMI data saved to database successfully!", "Success", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            else
            {
                MessageBox.Show("Failed to save data to database.", "Error", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
            }
        }

        private void cmdViewHistory_Click(object sender, EventArgs e)
        {
            // Create a simple form to view history
            object rs;
            string msg = "";
            int recordCount = 0;
            
            // Get records for the current person if name is entered, otherwise get all
            if (txtName.Text.Trim().Length > 0)
            {
                rs = DatabaseHelper.GetPersonBMIRecords(txtName.Text);
                msg = "BMI History for " + txtName.Text + "\r\n";
            }
            else
            {
                rs = DatabaseHelper.GetAllBMIRecords();
                msg = "All BMI Records\r\n";
            }
            
            msg = msg + new string('-', 60) + "\r\n";
            
            if (rs != null)
            {
                var records = (System.Collections.Generic.List<BMIRecord>)rs;
                if (records.Count > 0)
                {
                    recordCount = 0;
                    foreach (var record in records)
                    {
                        if (recordCount >= 10) break; // Show last 10 records
                        
                        msg = msg + record.DateRecorded.ToString("yyyy-MM-dd HH:mm") + " | ";
                        msg = msg + record.PersonName + " | ";
                        msg = msg + "H: " + record.Height + "cm | ";
                        msg = msg + "W: " + record.Weight + "kg | ";
                        msg = msg + "BMI: " + record.BMI.ToString("0.00") + " | ";
                        msg = msg + record.Category + "\r\n";
                        recordCount++;
                    }
                    
                    if (records.Count > 10)
                    {
                        msg = msg + "\r\n(Showing last 10 records)";
                    }
                }
                else
                {
                    msg = msg + "No records found.";
                }
            }
            else
            {
                msg = msg + "Unable to retrieve records.";
            }
            
            MessageBox.Show(msg, "BMI History", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }

        private void cmdStats_Click(object sender, EventArgs e)
        {
            // Show statistics for a person
            string personName = Microsoft.VisualBasic.Interaction.InputBox(
                "Enter name to view statistics (leave blank for current):", 
                "View Statistics", 
                txtName.Text);
            
            if (personName.Trim().Length == 0)
            {
                MessageBox.Show("Please enter a name to view statistics.", "Error", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
                return;
            }
            
            string stats = DatabaseHelper.GetPersonStats(personName);
            MessageBox.Show(stats, "BMI Statistics", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }

        // Optional: Add Enter key support for textboxes
        private void txtName_KeyPress(object sender, KeyPressEventArgs e)
        {
            if (e.KeyChar == (char)13) // Enter key
            {
                txtHeight.Focus();
            }
        }

        private void txtHeight_KeyPress(object sender, KeyPressEventArgs e)
        {
            if (e.KeyChar == (char)13) // Enter key
            {
                txtWeight.Focus();
            }
        }

        private void txtWeight_KeyPress(object sender, KeyPressEventArgs e)
        {
            if (e.KeyChar == (char)13) // Enter key
            {
                cmdCalculate_Click(sender, e);
            }
        }

        private void Mainfrm_FormClosing(object sender, FormClosingEventArgs e)
        {
            // Clean up
            objPerson = null;
            
            // Close database connection
            DatabaseHelper.CloseDatabase();
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }
    }
}