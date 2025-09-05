using System.ComponentModel;
using System.Drawing;
using System.Windows.Forms;

namespace BMI.UI
{
    partial class Mainfrm
    {
        private IContainer components = null;
        
        private TextBox txtHeight;
        private TextBox txtWeight;
        private TextBox txtName;
        private Button cmdCalculate;
        private Button cmdClear;
        private Button cmdSave;
        private Button cmdViewHistory;
        private Button cmdStats;
        private Label lblHeight;
        private Label lblWeight;
        private Label lblName;
        private Label lblResult;
        private Label lblIdealWeight;
        
        private void InitializeComponent()
        {
            this.txtHeight = new TextBox();
            this.txtWeight = new TextBox();
            this.txtName = new TextBox();
            this.cmdCalculate = new Button();
            this.cmdClear = new Button();
            this.cmdSave = new Button();
            this.cmdViewHistory = new Button();
            this.cmdStats = new Button();
            this.lblHeight = new Label();
            this.lblWeight = new Label();
            this.lblName = new Label();
            this.lblResult = new Label();
            this.lblIdealWeight = new Label();
            this.SuspendLayout();
            
            // lblName
            this.lblName.Text = "Name:";
            this.lblName.Location = new Point(33, 20);
            this.lblName.Size = new Size(80, 20);
            this.lblName.Visible = true;
            
            // txtName
            this.txtName.Location = new Point(120, 20);
            this.txtName.Size = new Size(200, 20);
            this.txtName.Text = "";
            this.txtName.Visible = true;
            this.txtName.KeyPress += new KeyPressEventHandler(this.txtName_KeyPress);
            
            // lblHeight
            this.lblHeight.Text = "Height (cm):";
            this.lblHeight.Location = new Point(33, 53);
            this.lblHeight.Size = new Size(80, 20);
            this.lblHeight.Visible = true;
            
            // txtHeight
            this.txtHeight.Location = new Point(120, 53);
            this.txtHeight.Size = new Size(133, 20);
            this.txtHeight.Text = "";
            this.txtHeight.Visible = true;
            this.txtHeight.KeyPress += new KeyPressEventHandler(this.txtHeight_KeyPress);
            
            // lblWeight
            this.lblWeight.Text = "Weight (kg):";
            this.lblWeight.Location = new Point(33, 87);
            this.lblWeight.Size = new Size(80, 20);
            this.lblWeight.Visible = true;
            
            // txtWeight
            this.txtWeight.Location = new Point(120, 87);
            this.txtWeight.Size = new Size(133, 20);
            this.txtWeight.Text = "";
            this.txtWeight.Visible = true;
            this.txtWeight.KeyPress += new KeyPressEventHandler(this.txtWeight_KeyPress);
            
            // cmdCalculate
            this.cmdCalculate.Text = "Calculate BMI";
            this.cmdCalculate.Location = new Point(33, 127);
            this.cmdCalculate.Size = new Size(87, 27);
            this.cmdCalculate.Visible = true;
            this.cmdCalculate.Click += new EventHandler(this.cmdCalculate_Click);
            
            // cmdClear
            this.cmdClear.Text = "Clear";
            this.cmdClear.Location = new Point(127, 127);
            this.cmdClear.Size = new Size(87, 27);
            this.cmdClear.Visible = true;
            this.cmdClear.Click += new EventHandler(this.cmdClear_Click);
            
            // cmdSave
            this.cmdSave.Text = "Save to DB";
            this.cmdSave.Location = new Point(220, 127);
            this.cmdSave.Size = new Size(87, 27);
            this.cmdSave.Visible = true;
            this.cmdSave.Enabled = false;
            this.cmdSave.Click += new EventHandler(this.cmdSave_Click);
            
            // cmdViewHistory
            this.cmdViewHistory.Text = "View History";
            this.cmdViewHistory.Location = new Point(313, 127);
            this.cmdViewHistory.Size = new Size(87, 27);
            this.cmdViewHistory.Visible = true;
            this.cmdViewHistory.Click += new EventHandler(this.cmdViewHistory_Click);
            
            // cmdStats
            this.cmdStats.Text = "Statistics";
            this.cmdStats.Location = new Point(167, 293);
            this.cmdStats.Size = new Size(100, 27);
            this.cmdStats.Visible = true;
            this.cmdStats.Click += new EventHandler(this.cmdStats_Click);
            
            // lblResult
            this.lblResult.Text = "";
            this.lblResult.Location = new Point(33, 167);
            this.lblResult.Size = new Size(367, 80);
            this.lblResult.Visible = true;
            this.lblResult.BackColor = SystemColors.Window;
            this.lblResult.BorderStyle = BorderStyle.FixedSingle;
            
            // lblIdealWeight
            this.lblIdealWeight.Text = "";
            this.lblIdealWeight.Location = new Point(33, 253);
            this.lblIdealWeight.Size = new Size(367, 20);
            this.lblIdealWeight.Visible = true;
            this.lblIdealWeight.TextAlign = ContentAlignment.MiddleCenter;
            
            // Form properties
            this.AutoScaleDimensions = new SizeF(6F, 13F);
            this.AutoScaleMode = AutoScaleMode.Font;
            this.ClientSize = new Size(776, 317);
            this.Name = "Mainfrm";
            this.Text = "Form1";
            this.StartPosition = FormStartPosition.WindowsDefaultLocation;
            this.Load += new EventHandler(this.Mainfrm_Load);
            this.FormClosing += new FormClosingEventHandler(this.Mainfrm_FormClosing);
            
            // Add controls to form
            this.Controls.Add(this.lblName);
            this.Controls.Add(this.txtName);
            this.Controls.Add(this.lblHeight);
            this.Controls.Add(this.txtHeight);
            this.Controls.Add(this.lblWeight);
            this.Controls.Add(this.txtWeight);
            this.Controls.Add(this.cmdCalculate);
            this.Controls.Add(this.cmdClear);
            this.Controls.Add(this.cmdSave);
            this.Controls.Add(this.cmdViewHistory);
            this.Controls.Add(this.cmdStats);
            this.Controls.Add(this.lblResult);
            this.Controls.Add(this.lblIdealWeight);
            
            this.ResumeLayout(false);
            this.PerformLayout();
        }
    }
}