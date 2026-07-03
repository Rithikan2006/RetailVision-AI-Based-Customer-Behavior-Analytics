import os
from datetime import datetime
from fpdf import FPDF
from database import get_total_visitors_count, get_average_stay_time, get_zone_visits_and_dwell

class RetailPDF(FPDF):
    def header(self):
        self.set_fill_color(30, 41, 59)
        self.rect(0, 0, 210, 40, 'F')
        
        self.set_text_color(255, 255, 255)
        self.set_font('Helvetica', 'B', 22)
        self.cell(0, 12, 'RetailVision', 0, 1, 'L')
        self.set_font('Helvetica', 'B', 10)
        self.cell(0, 5, 'AI-BASED CUSTOMER BEHAVIOR ANALYTICS REPORT', 0, 1, 'L')
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_text_color(128, 128, 128)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | RetailVision System', 0, 0, 'L')
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'R')

def generate_pdf_report(filename="daily_report.pdf"):
    pdf = RetailPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_text_color(51, 65, 85)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(100, 6, f"Store: Main Retail Branch #101", 0, 0)
    pdf.cell(90, 6, f"Report Period: Last 24 Hours", 0, 1, 'R')
    pdf.cell(100, 6, f"Manager ID: admin_01", 0, 0)
    pdf.cell(90, 6, f"Date: {datetime.now().strftime('%Y-%m-%d')}", 0, 1, 'R')
    pdf.ln(8)
    
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 10, "Executive Summary", 0, 1)
    
    total_visitors = get_total_visitors_count()
    avg_dwell = get_average_stay_time()
    
    # Draw KPI cards
    pdf.set_fill_color(248, 250, 252)
    pdf.rect(10, 65, 90, 25, 'F')
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(100, 116, 139)
    pdf.set_xy(15, 68)
    pdf.cell(80, 5, "TOTAL UNIQUE VISITORS", 0, 1)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(15, 23, 42)
    pdf.set_x(15)
    pdf.cell(80, 8, f"{total_visitors}", 0, 1)
    
    pdf.rect(110, 65, 90, 25, 'F')
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(100, 116, 139)
    pdf.set_xy(115, 68)
    pdf.cell(80, 5, "AVERAGE STAY DURATION", 0, 1)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(15, 23, 42)
    pdf.set_x(115)
    pdf.cell(80, 8, f"{avg_dwell} seconds", 0, 1)
    
    pdf.set_xy(10, 98)
    
    # Table breakdown
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, "Zone Dwell Time & Visits Breakdown", 0, 1)
    pdf.ln(2)
    
    pdf.set_fill_color(226, 232, 240)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(70, 8, " Zone Name", 1, 0, 'L', True)
    pdf.cell(60, 8, " Total Unique Visits", 1, 0, 'C', True)
    pdf.cell(60, 8, " Avg Dwell Time", 1, 1, 'C', True)
    
    zone_data = get_zone_visits_and_dwell()
    pdf.set_font('Helvetica', '', 10)
    for zone, stats in zone_data.items():
        pdf.cell(70, 8, f" {zone}", 1, 0, 'L')
        pdf.cell(60, 8, f" {stats['visits']}", 1, 0, 'C')
        pdf.cell(60, 8, f" {stats['avg_dwell']}s", 1, 1, 'C')
        
    pdf.ln(6)
    
    static_heatmap = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'heatmap.png')
    if os.path.exists(static_heatmap):
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, "Store Traffic Heatmap Visualization", 0, 1)
        pdf.ln(2)
        pdf.image(static_heatmap, x=10, y=pdf.get_y(), w=190, h=95)
        pdf.set_y(pdf.get_y() + 98)
    
    if pdf.get_y() > 220:
        pdf.add_page()
        
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, "Data-Driven Store Optimization Recommendations", 0, 1)
    pdf.ln(2)
    
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(51, 65, 85)
    
    recs = []
    billing_stats = zone_data.get('Billing', {'visits': 0, 'avg_dwell': 0})
    if billing_stats['avg_dwell'] > 60:
        recs.append("- High billing dwell time detected. Consider opening supplementary cash registers during peak periods.")
    else:
        recs.append("- Billing queues are flowing efficiently. Maintain current cashier schedules.")
        
    veg_stats = zone_data.get('Vegetables', {'visits': 0, 'avg_dwell': 0})
    snacks_stats = zone_data.get('Snacks', {'visits': 0, 'avg_dwell': 0})
    if veg_stats['visits'] > snacks_stats['visits']:
        recs.append("- Vegetables zone displays high customer traffic. Place high-margin items or promotional offers in the adjoining aisles to maximize exposure.")
    else:
        recs.append("- Snacks and beverages aisles are drawing high customer volumes. Ensure premium shelves are well-stocked and clean.")
        
    recs.append("- Ensure low-traffic zones identified in blue on the heatmap are evaluated for product selection updates or placement of eye-catching signage.")
    
    for r in recs:
        pdf.multi_cell(0, 6, r)
        pdf.ln(1)
        
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    report_path = os.path.join(reports_dir, filename)
    pdf.output(report_path)
    print(f"PDF Report saved to reports/{filename}")
    return report_path

if __name__ == '__main__':
    from database import init_db
    from heatmap import generate_heatmap
    init_db()
    generate_heatmap()
    generate_pdf_report()