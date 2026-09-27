from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import os

def create_pdf(path):
    c = canvas.Canvas(path, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 24)
    c.drawString(100, height - 100, "Introduction to Machine Learning")
    
    # Body
    c.setFont("Helvetica", 12)
    text = """
    Machine Learning is a field of inquiry devoted to understanding and building methods that 'learn', 
    that is, methods that leverage data to improve performance on some set of tasks. 
    It is seen as a part of artificial intelligence.
    
    Machine learning algorithms build a model based on sample data, known as training data, 
    in order to make predictions or decisions without being explicitly programmed to do so.
    
    Supervised learning algorithms build a mathematical model of a set of data that contains 
    both the inputs and the desired outputs. The data is known as training data, and consists 
    of a set of training examples.
    
    Unsupervised learning algorithms take a set of data that contains only inputs, and find 
    structure in the data, like grouping or clustering of data points.
    
    Reinforcement learning is an area of machine learning concerned with how software agents 
    ought to take actions in an environment in order to maximize the notion of cumulative reward.
    """
    
    y = height - 150
    for line in text.strip().split('\n'):
        c.drawString(72, y, line.strip())
        y -= 20
        
    c.save()

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to backend, then to test_data
    output_dir = os.path.join(os.path.dirname(current_dir), 'test_data')
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_path = os.path.join(output_dir, 'test_content.pdf')
    create_pdf(output_path)
    print(f"Created {output_path}")
