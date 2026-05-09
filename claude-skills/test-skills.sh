#!/bin/bash
# 完整测试脚本 — 验证 Skills 系统所有组件

set -e

SKILLS_DIR="$HOME/.claude/skills"
TEST_SKILL="discord-bot-diagnostics"
TEST_SKILL_PATH="$SKILLS_DIR/$TEST_SKILL"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 测试计数
TESTS_PASSED=0
TESTS_FAILED=0

# 测试辅助函数
test_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}🧪 $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

test_passed() {
    echo -e "${GREEN}✅ $1${NC}"
    ((TESTS_PASSED++))
}

test_failed() {
    echo -e "${RED}❌ $1${NC}"
    ((TESTS_FAILED++))
}

test_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# ===== Test 1: Git Configuration =====
test_section "Test 1: Git Configuration"

cd "$SKILLS_DIR" || {
    test_failed "Cannot cd to $SKILLS_DIR"
    exit 1
}

# Check .git exists
if [[ -d .git ]]; then
    test_passed ".git directory exists"
else
    test_failed ".git directory not found"
fi

# Check git config
GIT_USER=$(git config user.name 2>/dev/null || echo "")
if [[ -n "$GIT_USER" ]]; then
    test_passed "Git user configured: $GIT_USER"
else
    test_failed "Git user not configured"
fi

# ===== Test 2: Git Status =====
test_section "Test 2: Git Status"

GIT_STATUS=$(git status --short 2>/dev/null | wc -l)
echo "Current Git changes: $GIT_STATUS files"

if git status >/dev/null 2>&1; then
    test_passed "Git repository is healthy"
else
    test_failed "Git repository error"
fi

# ===== Test 3: Skill Files =====
test_section "Test 3: Skill Files"

# Check test skill exists
if [[ -d "$TEST_SKILL_PATH" ]]; then
    test_passed "Test skill directory exists: $TEST_SKILL"
else
    test_failed "Test skill directory not found: $TEST_SKILL"
    exit 1
fi

# Check skill.json
if [[ -f "$TEST_SKILL_PATH/skill.json" ]]; then
    test_passed "skill.json exists"

    # Validate JSON
    if python3 -m json.tool "$TEST_SKILL_PATH/skill.json" >/dev/null 2>&1; then
        test_passed "skill.json is valid JSON"
    else
        test_failed "skill.json is invalid JSON"
    fi
else
    test_failed "skill.json not found"
fi

# Check SKILL.md
if [[ -f "$TEST_SKILL_PATH/SKILL.md" ]]; then
    test_passed "SKILL.md exists"
    MD_SIZE=$(wc -c <"$TEST_SKILL_PATH/SKILL.md")
    echo "  File size: $MD_SIZE bytes"
else
    test_failed "SKILL.md not found"
fi

# ===== Test 4: Python Scripts =====
test_section "Test 4: Python Scripts Syntax"

SCRIPTS=(
    "skill-to-letta.py"
    "skill-update-hook.py"
)

for script in "${SCRIPTS[@]}"; do
    if [[ -f "$SKILLS_DIR/$script" ]]; then
        if python3 -m py_compile "$SKILLS_DIR/$script" 2>/dev/null; then
            test_passed "$script syntax is valid"
        else
            test_failed "$script has syntax errors"
        fi
    else
        test_failed "$script not found"
    fi
done

# ===== Test 5: Script Permissions =====
test_section "Test 5: Script Permissions"

SCRIPTS_WITH_EXEC=(
    "skill-sync.sh"
    "skill-to-letta.py"
    "skill-update-hook.py"
)

for script in "${SCRIPTS_WITH_EXEC[@]}"; do
    if [[ -f "$SKILLS_DIR/$script" ]]; then
        if [[ -x "$SKILLS_DIR/$script" ]]; then
            test_passed "$script is executable"
        else
            test_warn "$script is not executable (chmod +x needed)"
        fi
    fi
done

# ===== Test 6: Systemd Timer Configuration =====
test_section "Test 6: Systemd Timer Configuration"

TIMER_PATH="$HOME/.config/systemd/user/skill-sync.timer"
SERVICE_PATH="$HOME/.config/systemd/user/skill-sync.service"

if [[ -f "$TIMER_PATH" ]]; then
    test_passed "skill-sync.timer exists"
else
    test_failed "skill-sync.timer not found"
fi

if [[ -f "$SERVICE_PATH" ]]; then
    test_passed "skill-sync.service exists"
else
    test_failed "skill-sync.service not found"
fi

# ===== Test 7: Systemd Timer Status =====
test_section "Test 7: Systemd Timer Status"

if systemctl --user list-timers >/dev/null 2>&1; then
    TIMER_STATUS=$(systemctl --user list-timers --all 2>/dev/null | grep skill-sync || echo "")

    if [[ -n "$TIMER_STATUS" ]]; then
        test_passed "skill-sync.timer registered in systemd"
        echo "$TIMER_STATUS"
    else
        test_warn "skill-sync.timer not enabled yet (run: systemctl --user enable skill-sync.timer)"
    fi
else
    test_warn "Cannot check systemd timer status (user timers not available?)"
fi

# ===== Test 8: skill-sync.sh Execution =====
test_section "Test 8: skill-sync.sh Execution (Dry Run)"

if bash -n "$SKILLS_DIR/skill-sync.sh" 2>/dev/null; then
    test_passed "skill-sync.sh bash syntax is valid"
else
    test_failed "skill-sync.sh has bash syntax errors"
fi

# ===== Test 9: Directory Structure =====
test_section "Test 9: Skill Directory Structure"

SKILL_COUNT=$(find "$SKILLS_DIR" -maxdepth 1 -type d ! -name ".*" | wc -l)
echo "Total skill directories: $(($SKILL_COUNT - 1))"  # Subtract 1 for parent

if [[ $(($SKILL_COUNT - 1)) -gt 0 ]]; then
    test_passed "Multiple skills found"
else
    test_warn "No skills found"
fi

# ===== Test 10: .gitignore =====
test_section "Test 10: Git Ignore Rules"

if [[ -f "$SKILLS_DIR/.gitignore" ]]; then
    test_passed ".gitignore exists"

    # Check for common patterns
    if grep -q "*.pyc" "$SKILLS_DIR/.gitignore"; then
        test_passed ".gitignore includes *.pyc"
    fi

    if grep -q "__pycache__" "$SKILLS_DIR/.gitignore"; then
        test_passed ".gitignore includes __pycache__"
    fi
else
    test_failed ".gitignore not found"
fi

# ===== Test 11: Log File =====
test_section "Test 11: Log File Setup"

LOG_FILE="$SKILLS_DIR/.sync.log"

if [[ -f "$LOG_FILE" ]]; then
    test_passed "Log file exists: $LOG_FILE"
    LINES=$(wc -l <"$LOG_FILE")
    echo "  Log entries: $LINES lines"
else
    echo "Log file will be created on first sync"
fi

# ===== Test 12: Optional - Letta Connection Test =====
test_section "Test 12: Optional - Letta Connection Test"

LETTA_URL="${LETTA_API_URL:-http://localhost:8283}"

echo "Testing Letta connection at: $LETTA_URL"

if curl -s --connect-timeout 3 "$LETTA_URL/v1/status" >/dev/null 2>&1; then
    test_passed "Letta API is reachable"
else
    test_warn "Letta API not reachable at $LETTA_URL (optional)"
    echo "  To enable Letta integration, ensure Letta service is running"
    echo "  Set LETTA_API_URL env var if using non-standard address"
fi

# ===== Summary =====
test_section "Test Summary"

TOTAL=$((TESTS_PASSED + TESTS_FAILED))

echo ""
echo -e "Total Tests: ${BLUE}$TOTAL${NC}"
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ All Tests Passed!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Enable Systemd Timer:"
    echo "     systemctl --user enable --now skill-sync.timer"
    echo ""
    echo "  2. Run manual sync:"
    echo "     bash ~/.claude/skills/skill-sync.sh"
    echo ""
    echo "  3. Test Skill auto-update:"
    echo "     python3 ~/.claude/skills/skill-update-hook.py 'Discord bot not responding'"
    echo ""
    exit 0
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}❌ Some Tests Failed${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  - Check file permissions: ls -la ~/.claude/skills/"
    echo "  - Check Python syntax: python3 -m py_compile script.py"
    echo "  - Check Git config: cd ~/.claude/skills && git config --list"
    echo ""
    exit 1
fi
