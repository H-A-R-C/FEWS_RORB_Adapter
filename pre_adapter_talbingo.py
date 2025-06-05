import sys
from src import PreAdapter

def print_help():
    print("Usage: python script_name.py <input_file>")
    print("This script takes one argument: <input_file> which is used to create a batch file.")
    print("Example: python script_name.py data.txt")

if __name__ == "__main__":
    # Check if the user asked for help or if the number of arguments is incorrect
    if len(sys.argv) != 2 or sys.argv[1] in ['-h', '--help']:
        print_help()
    else:
        runinfo_xml = sys.argv[1]
        try:
            # Attempt to create a batch file with the provided input file
            PreAdapter.write_template_files(runinfo_xml)
            print(f"Batch file created successfully using {runinfo_xml}")
        except Exception as e:
            print(f"An error occurred: {e}")
            print("Please check the input file and try again.")
