using System;

namespace BMI.Models
{
    /// <summary>
    /// Converted from VB6 class module: CPerson
    /// This class handles person data and BMI calculations
    /// </summary>
    public class CPerson
    {
        // Private fields
        private string _name;
        private double _height;
        private double _weight;
        private double _bmi;
        private string _category;

        /// <summary>
        /// Initializes a new instance of the CPerson class
        /// </summary>
        public CPerson()
        {
            _name = string.Empty;
            _height = 0;
            _weight = 0;
            _bmi = 0;
            _category = string.Empty;
        }

        /// <summary>
        /// Gets or sets the person's name
        /// </summary>
        public string Name
        {
            get { return _name; }
            set { _name = value; }
        }

        /// <summary>
        /// Gets or sets the person's height in centimeters
        /// </summary>
        public double Height
        {
            get { return _height; }
            set
            {
                if (value > 0)
                {
                    _height = value;
                    CalculateBMI();
                }
                else
                {
                    throw new ArgumentException("Height must be positive", nameof(value));
                }
            }
        }

        /// <summary>
        /// Gets or sets the person's weight in kilograms
        /// </summary>
        public double Weight
        {
            get { return _weight; }
            set
            {
                if (value > 0)
                {
                    _weight = value;
                    CalculateBMI();
                }
                else
                {
                    throw new ArgumentException("Weight must be positive", nameof(value));
                }
            }
        }

        /// <summary>
        /// Gets the calculated BMI value
        /// </summary>
        public double BMI
        {
            get { return _bmi; }
        }

        /// <summary>
        /// Gets the BMI category
        /// </summary>
        public string Category
        {
            get { return _category; }
        }

        /// <summary>
        /// Calculates BMI and determines category
        /// </summary>
        private void CalculateBMI()
        {
            if (_height > 0 && _weight > 0)
            {
                _bmi = _weight / Math.Pow(_height / 100, 2);
                _category = GetBMICategory(_bmi);
            }
        }

        /// <summary>
        /// Determines BMI category based on BMI value
        /// </summary>
        /// <param name="bmi">BMI value</param>
        /// <returns>BMI category string</returns>
        private string GetBMICategory(double bmi)
        {
            if (bmi < 18.5)
                return "Underweight";
            else if (bmi >= 18.5 && bmi <= 24.99)
                return "Normal weight";
            else if (bmi >= 25 && bmi <= 29.99)
                return "Overweight";
            else
                return "Obese";
        }

        /// <summary>
        /// Generates a formatted BMI report
        /// </summary>
        /// <returns>Formatted BMI report string</returns>
        public string GetBMIReport()
        {
            if (_bmi > 0)
            {
                var report = "BMI Report" + Environment.NewLine;
                report += new string('-', 30) + Environment.NewLine;
                
                if (!string.IsNullOrEmpty(_name))
                {
                    report += $"Name: {_name}" + Environment.NewLine;
                }
                
                report += $"Height: {_height:0.00} cm" + Environment.NewLine;
                report += $"Weight: {_weight:0.00} kg" + Environment.NewLine;
                report += $"BMI: {_bmi:0.00}" + Environment.NewLine;
                report += $"Category: {_category}" + Environment.NewLine;
                report += new string('-', 30);
                
                return report;
            }
            else
            {
                return "No BMI data available";
            }
        }
    }
}