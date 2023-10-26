import os
import re
import logging
import subprocess

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def is_binary_string(bytes_content):
    """Determine if a byte sequence contains binary data."""
    textchars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7F})
    return bool(bytes_content.translate(None, textchars))


def is_binary_file(filepath):
    """Check if a file is binary using the provided heuristic."""
    try:
        with open(filepath, "rb") as file:
            return is_binary_string(file.read(1024))
    except Exception as e:
        logging.error(f"Error reading file {filepath}: {e}")
        return False


def list_git_files_and_dirs(directory):
    """Get a list of text-based files and their directories tracked by Git in the given directory."""
    os.chdir(directory)
    result = subprocess.run(["git", "ls-files"], stdout=subprocess.PIPE)
    files = result.stdout.decode("utf-8").splitlines()

    # Corrected the path passed to is_binary_file function
    text_files = [f for f in files if not is_binary_file(os.path.join(directory, f))]
    dirs = set(os.path.dirname(f) for f in text_files)

    logging.info(f"Matched text files: {text_files}")
    return text_files, dirs


def write_to_markdown(directory, outfile, exclude_patterns=[]):
    """Generate a markdown file for the given directory."""
    logging.info(f"Starting to write markdown for directory: {directory}")
    with open(outfile, "w", encoding="utf-8") as md_file:
        # Use only the directory name for header 1
        dirname = os.path.basename(directory)
        md_file.write(f"# {dirname}\n\n")

        # Get text-based files and their directories tracked by Git
        text_files, dirs = list_git_files_and_dirs(directory)
        dirs = []
        if not text_files:
            logging.warning(f"No text files found in directory: {directory}")
            return

        # Filter out files matching the exclude patterns
        for pattern in exclude_patterns:
            text_files = [f for f in text_files if not re.search(pattern, f)]

        # Combine directories and files and sort them for structured output
        # Convert dirs set to a list before concatenating
        all_items = sorted(list(dirs) + text_files, key=lambda x: (x.count("/"), x))

        # Write directories and files to markdown
        for item in all_items:
            header_level = item.count("/") + 2
            md_file.write("#" * header_level + f" {item}\n")

            if item in text_files:
                # Open with utf-8 encoding
                with open(
                    os.path.join(directory, item),
                    "r",
                    encoding="utf-8",
                    errors="replace",
                ) as content_file:
                    md_file.write(f"```\n")
                    md_file.write(content_file.read())
                    md_file.write("\n```\n\n")
                logging.info(f"Added content for file: {item}")

    logging.info(f"Markdown file written to: {outfile}")


# This is just to demonstrate the function
# In a real scenario, this would be invoked from the command line
demo_directory = "V:\Code\cnc-monitoring-system"
demo_outfile = "structure.md"
exclude_patterns = [r"normalize.css", r"chart.js", r"socket.io.js"]

# Generate a markdown file for the demo directory
write_to_markdown(demo_directory, demo_outfile, exclude_patterns)
