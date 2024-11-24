from flask import Flask, render_template, request, redirect, url_for, send_file
import csv
import datetime
from io import StringIO, BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import io

app = Flask(__name__)

FILE_NAME = "expenses.csv"

# Function to add an expense
def add_expense(description, amount, category):
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(FILE_NAME, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([date, description, amount, category])

# Function to get all expenses
def get_expenses(currency='INR', days=0):
    expenses = []
    try:
        with open(FILE_NAME, mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                date = datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                if days > 0:
                    # Filter by date
                    if (datetime.datetime.now() - date).days > days:
                        continue
                amount = float(row[2])
                if currency == 'USD':
                    amount *= 0.012  # Example conversion rate INR to USD
                elif currency == 'EUR':
                    amount *= 0.011  # Example conversion rate INR to EUR
                expenses.append([date.strftime("%Y-%m-%d"), row[1], round(amount, 2), row[3]])
    except FileNotFoundError:
        pass
    return expenses

# Function to calculate the total expenses
def calculate_total(currency='INR', days=0):
    total = 0
    expenses = get_expenses(currency, days)
    for expense in expenses:
        total += expense[2]  # Expense amount (adjusted currency)
    return round(total, 2)

# Function to calculate monthly summary
def get_monthly_summary(currency='INR', days=0):
    monthly_expenses = {}
    expenses = get_expenses(currency, days)  # Get filtered expenses based on currency and days
    for expense in expenses:
        date = expense[0]  # Date is in YYYY-MM-DD format
        amount = expense[2]  # Adjusted amount based on the selected currency
        month = date[:7]  # Extract year-month (e.g., 2024-11)
        if month in monthly_expenses:
            monthly_expenses[month] += amount
        else:
            monthly_expenses[month] = amount
    return monthly_expenses

# Function to generate a CSV of filtered expenses
def generate_csv(expenses):
    # Create a BytesIO object to hold the CSV data in memory
    output = io.BytesIO()
    writer = csv.writer(output)
    
    # Write the header row
    writer.writerow(["Date", "Description", "Amount", "Category"])
    
    # Write the expense data
    for expense in expenses:
        writer.writerow(expense)
    
    # Seek to the beginning of the BytesIO object before returning it
    output.seek(0)
    return output
# Function to generate a PDF of filtered expenses
def generate_pdf(expenses):
    output = BytesIO()  # Use BytesIO for binary content like PDFs
    pdf_file = canvas.Canvas(output, pagesize=letter)
    pdf_width, pdf_height = letter  # Get the width and height of the letter page size

    # Title
    pdf_file.setFont("Helvetica-Bold", 16)
    pdf_file.drawString(200, pdf_height - 40, "Expenses Report")
    
    # Table Headers
    pdf_file.setFont("Helvetica-Bold", 10)
    pdf_file.drawString(50, pdf_height - 80, "Date")
    pdf_file.drawString(150, pdf_height - 80, "Description")
    pdf_file.drawString(300, pdf_height - 80, "Amount")
    pdf_file.drawString(450, pdf_height - 80, "Category")
    
    # Line below header
    pdf_file.line(50, pdf_height - 85, pdf_width - 50, pdf_height - 85)
    
    # Start drawing rows from here
    y_position = pdf_height - 100  # Start position for the rows
    row_height = 18  # Adjusted row height for better spacing
    pdf_file.setFont("Helvetica", 10)
    
    # Loop through the expenses and add them to the table
    for i, expense in enumerate(expenses):
        date, description, amount, category = expense
        
        # Before drawing the text, handle the background color
        if i % 2 == 0:  # Alternate row color for readability
            pdf_file.setFillColor(colors.lightgrey)
            pdf_file.rect(50, y_position - 3, pdf_width - 100, row_height, fill=True, stroke=False)
            pdf_file.setFillColor(colors.black)  # Reset fill color

        # Draw the row data (text) on top of the background
        pdf_file.drawString(50, y_position, date)
        pdf_file.drawString(150, y_position, description)
        pdf_file.drawString(300, y_position, str(amount))
        pdf_file.drawString(450, y_position, category)

        # Move y_position down for the next row
        y_position -= row_height

        # Add a page break if necessary
        if y_position < 100:
            pdf_file.showPage()
            pdf_file.setFont("Helvetica-Bold", 16)
            pdf_file.drawString(200, pdf_height - 40, "Expenses Report")
            pdf_file.setFont("Helvetica-Bold", 10)
            pdf_file.drawString(50, pdf_height - 80, "Date")
            pdf_file.drawString(150, pdf_height - 80, "Description")
            pdf_file.drawString(300, pdf_height - 80, "Amount")
            pdf_file.drawString(450, pdf_height - 80, "Category")
            pdf_file.line(50, pdf_height - 85, pdf_width - 50, pdf_height - 85)
            y_position = pdf_height - 100  # Reset the Y position for the next page
    
    # Save the PDF content
    pdf_file.save()
    output.seek(0)  # Reset pointer to the beginning of the BytesIO object
    return output


@app.route('/')
def index():
    currency = request.args.get('currency', 'INR')
    expenses = get_expenses(currency)
    total = calculate_total(currency)
    monthly_summary = get_monthly_summary(currency)
    currency_symbol = '₹' if currency == 'INR' else '$' if currency == 'USD' else '€'
    return render_template('index.html', expenses=expenses, total=total, monthly_summary=monthly_summary, currency_symbol=currency_symbol, currency=currency)

@app.route('/add', methods=['POST'])
def add():
    description = request.form['description']
    amount = float(request.form['amount'])
    category = request.form['category']
    add_expense(description, amount, category)
    return redirect(url_for('index'))

@app.route('/download', methods=['GET'])
def download():
    days = int(request.args.get('days', 7))
    format_type = request.args.get('format', 'pdf')
    currency = request.args.get('currency', 'INR')
    expenses = get_expenses(currency, days)
    
    if format_type == 'csv':
        csv_data = generate_csv(expenses)
        return send_file(csv_data, mimetype='text/csv', as_attachment=True, download_name="expenses.csv")
    elif format_type == 'pdf':
        pdf_data = generate_pdf(expenses)
        return send_file(pdf_data, mimetype='application/pdf', as_attachment=True, download_name="expenses.pdf")

# Run the app
if __name__ == "__main__":
    app.run(debug=True)
