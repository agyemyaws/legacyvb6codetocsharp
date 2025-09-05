using System;
using System.Collections.Generic;
using System.Data;
using System.Data.OleDb;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using System.Windows.Forms;
using System.Drawing;

namespace BMI.Utilities
{
    /// <summary>
    /// Converted from VB6 standard module: modUtilities
    /// This module contains utility functions and global constants for BMI calculations
    /// </summary>
    public static class ModUtilities
    {
        #region Public Constants
        
        public const double BMI_UNDERWEIGHT = 18.5;
        public const double BMI_NORMAL_MAX = 25.0;
        public const double BMI_OVERWEIGHT_MAX = 30.0;
        public const double IDEAL_BMI_MIN = 18.5;
        public const double IDEAL_BMI_MAX = 24.9;
        
        #endregion

        #region Private Constants
        
        private const double POUNDS_TO_KG_FACTOR = 0.453592;
        private const double KG_TO_POUNDS_FACTOR = 2.20462;
        private const double INCHES_TO_CM_FACTOR = 2.54;
        private const int INCHES_PER_FOOT = 12;
        
        #endregion

        #region Public Methods
        
        public static bool IsValidNumber(string strInput)
        {
            try
            {
                if (string.IsNullOrWhiteSpace(strInput))
                    return false;

                if (double.TryParse(strInput, out double result))
                {
                    return result > 0;
                }
                
                return false;
            }
            catch
            {
                return false;
            }
        }

        public static string GetIdealWeightRange(double heightCm)
        {
            if (heightCm <= 0)
                return "Invalid height";

            double heightM = heightCm / 100.0;
            double minWeight = IDEAL_BMI_MIN * (heightM * heightM);
            double maxWeight = IDEAL_BMI_MAX * (heightM * heightM);

            return $"{minWeight:F1} - {maxWeight:F1} kg";
        }

        public static double PoundsToKg(double pounds) => pounds * POUNDS_TO_KG_FACTOR;

        public static double KgToPounds(double kg) => kg * KG_TO_POUNDS_FACTOR;

        public static double FeetInchesToCm(int feet, double inches)
        {
            return (feet * INCHES_PER_FOOT + inches) * INCHES_TO_CM_FACTOR;
        }

        public static string CmToFeetInches(double cm)
        {
            double totalInches = cm / INCHES_TO_CM_FACTOR;
            int feet = (int)(totalInches / INCHES_PER_FOOT);
            double inches = totalInches - (feet * INCHES_PER_FOOT);

            return $"{feet}' {inches:F1}\"";
        }

        public static Color GetBMIColorCode(double bmi)
        {
            if (bmi < BMI_UNDERWEIGHT)
                return Color.Blue;
            else if (bmi < BMI_NORMAL_MAX)
                return Color.Green;
            else if (bmi < BMI_OVERWEIGHT_MAX)
                return Color.FromArgb(255, 165, 0);
            else
                return Color.Red;
        }

        public static void SaveBMIToFile(string name, double height, double weight, double bmi)
        {
            try
            {
                string filePath = Path.Combine(Application.StartupPath, "BMI_History.txt");
                
                using (var writer = new StreamWriter(filePath, true))
                {
                    writer.WriteLine($"{DateTime.Now}\t{name}\t{height}\t{weight}\t{bmi:F2}");
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error saving to file: {ex.Message}", "Error", 
                    MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
            }
        }

        public static void ClearTextBoxes(Form frm)
        {
            foreach (Control ctrl in frm.Controls)
            {
                if (ctrl is TextBox textBox)
                {
                    textBox.Text = string.Empty;
                }
            }
        }
        
        #endregion
    }
}