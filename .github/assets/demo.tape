# demo.tape - VHS recording script for the indo demo GIF
#
# Usage: vhs .github/assets/demo.tape (run from repository root)
#

# Output configuration
Output .github/assets/demo.gif

# Terminal appearance settings
Set Shell bash
Set FontSize 24
Set Width 1200
Set Height 400
Set Padding 20
Set TypingSpeed 75ms

# Setup the environment (hidden from viewer)
Hide
Type "export PS1='> '"
Enter
Type "chmod +x in.sh"
Enter
# Create a fresh demo directory
Type "rm -rf demo_env && mkdir -p demo_env/packages && cd demo_env/packages"
Enter
# Create subdirectories
Type "mkdir auth-service payment-service user-service"
Enter
Type "touch auth-service/package.json payment-service/package.json"
Enter
# Point 'indo' at the script in the root directory
Type "alias indo=../../in.sh"
Enter
Type "clear"
Enter
Show

# Scene 1: Batch File Operations
Set TypingSpeed 20ms
Type "# indo: create config files in all service folders"
Set TypingSpeed 75ms
Sleep 500ms
Enter
Type "indo *-service touch .env"
Sleep 800ms
Enter
Sleep 3s

# Clear for next scene
Hide
Type "clear"
Enter
Show
# Scene 2: Parallel Execution
Set TypingSpeed 20ms
Type "# Run build scripts in parallel"
Set TypingSpeed 75ms
Sleep 500ms
Enter
Type "indo -P 3 * 'echo building...; sleep 0.5'"
Sleep 800ms
Enter
Sleep 3s

# Clear for next scene
Hide
Type "clear"
Enter
Show
# Scene 3: Shell Features
Set TypingSpeed 20ms
Type "# Run shell commands with pipes and wildcards"
Set TypingSpeed 75ms
Sleep 500ms
Enter
Type "indo * 'ls -a | grep .env'"
Sleep 800ms
Enter
Sleep 3s

# Clear for next scene
Hide
Type "clear"
Enter
Show
# Scene 4: Short output for scripts and AI agents
Set TypingSpeed 20ms
Type "# Show only the folders that failed"
Set TypingSpeed 75ms
Sleep 500ms
Enter
Type "indo -f * 'test -f package.json'"
Sleep 800ms
Enter
Sleep 3s

# Cleanup (hidden)
Hide
Type "cd ../.."
Enter
Type "rm -rf demo_env"
Enter
