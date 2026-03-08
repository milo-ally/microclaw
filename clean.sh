#!/bin/bash

# Define the target directory (agent folder)
TARGET_DIR="agent"

# Define the list of directories to KEEP (case-sensitive)
KEEP_DIRS=(
    "memory"
    "sessions"
    "skills"
    "storage"
    "workplace"  # Included as it's in your directory structure
)

# Function to validate directory existence
check_directory() {
    if [ ! -d "$1" ]; then
        echo "Error: Directory '$1' does not exist. Exiting script."
        exit 1
    fi
}

# Main execution starts here
echo "=== Starting cleanup process ==="

# Step 1: Check if target directory exists
check_directory "$TARGET_DIR"

# Step 2: Navigate to target directory
echo "Navigating to directory: $TARGET_DIR"
cd "$TARGET_DIR" || {
    echo "Error: Failed to enter directory '$TARGET_DIR'. Exiting script."
    exit 1
}

# Step 3: Create a pattern for directories to keep (for extended globbing)
KEEP_PATTERN=$(IFS='|'; echo "${KEEP_DIRS[*]}")

# Step 4: Enable extended globbing to use advanced pattern matching
shopt -s extglob

# Step 5: Delete all files and directories EXCEPT the kept ones
echo "Removing all files and directories except: ${KEEP_DIRS[*]}"
rm -rf !($KEEP_PATTERN) 2>/dev/null

# Step 6: Disable extended globbing (clean up shell options)
shopt -u extglob

# Step 7: Verify cleanup completion
echo "Cleanup completed successfully!"
echo "Remaining directories in $TARGET_DIR:"
ls -d */ 2>/dev/null || echo "No directories found (this is unexpected!)"

echo "=== Cleanup process finished ==="
