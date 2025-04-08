# Rail Operations & Maintenance Optimizer

A tool to optimize the operational planning of rail vehicle traffic and maintenance over a 14-day horizon.

## Project Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Setting up the Development Environment

1. Create a virtual environment:
   ```
   # Windows
   python -m venv venv
   
   # Linux/macOS
   python3 -m venv venv
   ```

2. Activate the virtual environment:
   ```
   # Windows
   .\venv\Scripts\activate
   
   # Linux/macOS
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Project Structure

- `core/`: Contains the core optimization algorithms and logic
  - Future modules will include data models, constraints, and optimization solvers

## Development

This project uses Google OR-Tools for constraint programming to solve the rail operations and maintenance optimization problem.
