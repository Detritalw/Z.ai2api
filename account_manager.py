# -*- coding: utf-8 -*-
"""
Z.ai 账户管理器
使用方向键选择的控制台界面，管理多个 Z.ai 账户
"""

import curses
import json
import os
import sys
import requests
from datetime import datetime

# 配置文件路径
ACCOUNTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "accounts.json")
BASE_URL = "https://chat.z.ai"

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "X-FE-Version": "prod-fe-1.0.111",
    "sec-ch-ua": '"Microsoft Edge";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/",
}


def load_accounts():
    """加载账户列表"""
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_accounts(accounts):
    """保存账户列表"""
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(accounts, f, ensure_ascii=False, indent=2)


def validate_cookie(cookie_str):
    """验证 cookie 是否有效，返回用户信息或 None"""
    try:
        headers = {**BROWSER_HEADERS, "Cookie": cookie_str}
        r = requests.get(f"{BASE_URL}/api/v1/auths/", headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("id") and data.get("name"):
                return {
                    "user_id": data["id"],
                    "user_name": data["name"],
                    "token": data.get("token", ""),
                    "cookie": cookie_str,
                }
    except Exception:
        pass
    return None


def draw_menu(stdscr, title, options, current_idx, start_y=2):
    """绘制菜单"""
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    # 标题
    title_x = max(0, (w - len(title)) // 2)
    stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, title_x, title)
    stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

    # 菜单选项
    for idx, option in enumerate(options):
        x = max(0, (w - len(option)) // 2)
        y = start_y + idx
        if y >= h - 2:
            break
        if idx == current_idx:
            stdscr.attron(curses.color_pair(2))
            stdscr.addstr(y, x, f"> {option} <")
            stdscr.attroff(curses.color_pair(2))
        else:
            stdscr.addstr(y, x, option)

    # 底部提示
    help_text = "↑↓:移动  Enter:确认  q:返回"
    stdscr.attron(curses.color_pair(3))
    stdscr.addstr(h - 1, max(0, (w - len(help_text)) // 2), help_text)
    stdscr.attroff(curses.color_pair(3))

    stdscr.refresh()


def draw_account_list(stdscr, accounts, current_idx, scroll_offset):
    """绘制账户列表"""
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    title = "账户列表"
    title_x = max(0, (w - len(title)) // 2)
    stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, title_x, title)
    stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

    if not accounts:
        empty_text = "暂无账户，请先添加"
        stdscr.addstr(4, max(0, (w - len(empty_text)) // 2), empty_text)
    else:
        max_display = h - 5
        for i in range(max_display):
            idx = scroll_offset + i
            if idx >= len(accounts):
                break
            acc = accounts[idx]
            name = acc.get("user_name", "未知")
            label = acc.get("label", "")
            status = "✓" if acc.get("is_active", True) else "✗"
            display = f"{status} {name}"
            if label:
                display += f" ({label})"

            y = 3 + i
            x = max(2, (w - 40) // 2)

            if idx == current_idx:
                stdscr.attron(curses.color_pair(2))
                stdscr.addstr(y, x, f"> {display:<38}")
                stdscr.attroff(curses.color_pair(2))
            else:
                stdscr.addstr(y, x, f"  {display:<38}")

    # 底部提示
    help_text = "↑↓:移动  a:添加  b:批量导入  d:删除  e:编辑  Enter:切换  q:返回"
    stdscr.attron(curses.color_pair(3))
    stdscr.addstr(h - 1, max(0, (w - len(help_text)) // 2), help_text)
    stdscr.attroff(curses.color_pair(3))

    stdscr.refresh()


def get_input(stdscr, prompt, y, x, max_len=80):
    """获取用户输入"""
    h, w = stdscr.getmaxyx()
    stdscr.addstr(y, x, prompt)
    stdscr.refresh()

    input_y = y + 1
    input_x = x
    stdscr.addstr(input_y, input_x, "_" * min(max_len, w - input_x - 2))
    stdscr.move(input_y, input_x)

    chars = []
    while True:
        ch = stdscr.getch()
        if ch == 10:  # Enter
            break
        elif ch == 27:  # Escape
            return None
        elif ch in (curses.KEY_BACKSPACE, 127, 8):
            if chars:
                chars.pop()
                stdscr.addstr(input_y, input_x, " " * min(max_len, w - input_x - 2))
                stdscr.addstr(input_y, input_x, "".join(chars))
        elif 32 <= ch <= 126:
            if len(chars) < max_len:
                chars.append(chr(ch))
                stdscr.addstr(input_y, input_x, "".join(chars))
    return "".join(chars)


def batch_import_screen(stdscr, accounts):
    """批量导入账户界面 - 支持一行一个 Cookie"""
    h, w = stdscr.getmaxyx()
    stdscr.clear()

    title = "批量导入账户"
    title_x = max(0, (w - len(title)) // 2)
    stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, title_x, title)
    stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

    x = max(2, (w - 55) // 2)

    stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
    stdscr.addstr(3, x, "【批量导入说明】")
    stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)

    instructions = [
        "1. 每行一个 Cookie（支持从文本编辑器复制）",
        "2. 空行会自动跳过",
        "3. 粘贴后按 Enter 开始导入",
    ]

    for i, line in enumerate(instructions):
        stdscr.addstr(4 + i, x, line)

    stdscr.addstr(8, x, "─" * 50)
    stdscr.addstr(10, x, "请粘贴 Cookie（一行一个，粘贴完毕后按 Enter）:")
    stdscr.refresh()

    # 使用 Python 的 input 函数获取多行输入（更可靠的粘贴支持）
    curses.endwin()
    print("\n" + "=" * 60)
    print("请粘贴 Cookie（一行一个，粘贴完毕后按两次 Enter 结束）:")
    print("示例:")
    print("  cookie_value_1")
    print("  cookie_value_2")
    print("  cookie_value_3")
    print("  (空行结束)")
    print("=" * 60)

    cookies = []
    empty_count = 0
    while True:
        try:
            line = input()
            if line.strip():
                cookies.append(line.strip())
                empty_count = 0
            else:
                empty_count += 1
                if empty_count >= 2:
                    break
        except EOFError:
            break

    if not cookies:
        print("未输入任何 Cookie，返回...")
        print("=" * 60)
        # 恢复 curses
        _restore_curses(stdscr)
        return False

    print(f"\n已接收 {len(cookies)} 个 Cookie，正在验证...")
    print("=" * 60)

    # 恢复 curses
    _restore_curses(stdscr)

    # 逐个验证并导入
    success_count = 0
    fail_count = 0
    skip_exists = 0
    skip_duplicate = 0
    current_y = 12
    imported_cookies = set()  # 用于检测本次导入内的重复

    for i, cookie_str in enumerate(cookies):
        if current_y >= h - 3:
            # 屏幕已满，显示滚动提示
            stdscr.addstr(h - 3, x, f"... 处理中 ({i + 1}/{len(cookies)}) ...")
            stdscr.refresh()

        # 检查本次导入内是否有重复
        if cookie_str in imported_cookies:
            skip_duplicate += 1
            if current_y < h - 4:
                stdscr.addstr(current_y, x, f"⚠ 第 {i + 1} 个: 与前面重复，跳过")
                current_y += 1
            continue

        # 检查是否已存在于账户库
        exists = False
        for acc in accounts:
            if acc.get("cookie") == cookie_str:
                exists = True
                break

        if exists:
            skip_exists += 1
            if current_y < h - 4:
                stdscr.addstr(current_y, x, f"⚠ 第 {i + 1} 个: 已存在，跳过")
                current_y += 1
            continue

        # 验证 cookie 可用性
        user_info = validate_cookie(cookie_str)
        if not user_info:
            fail_count += 1
            if current_y < h - 4:
                stdscr.addstr(current_y, x, f"✗ 第 {i + 1} 个: Cookie 无效或网络错误")
                current_y += 1
            continue

        # 添加账户
        account = {
            "cookie": cookie_str,
            "token": user_info.get("token", ""),
            "user_id": user_info["user_id"],
            "user_name": user_info["user_name"],
            "label": "",
            "is_active": True,
            "added_at": datetime.now().isoformat(),
        }
        accounts.append(account)
        imported_cookies.add(cookie_str)
        success_count += 1

        if current_y < h - 4:
            stdscr.addstr(current_y, x, f"✓ 第 {i + 1} 个: {user_info['user_name']}")
            current_y += 1

    # 保存所有账户
    save_accounts(accounts)

    # 显示统计
    current_y += 1
    stdscr.addstr(current_y, x, "─" * 50)
    current_y += 1
    stdscr.addstr(current_y, x, f"导入完成！成功: {success_count}  失败: {fail_count}  已存在: {skip_exists}  重复: {skip_duplicate}")
    current_y += 2
    stdscr.addstr(current_y, x, "按任意键返回...")
    stdscr.refresh()
    stdscr.getch()

    return success_count > 0


def _restore_curses(stdscr):
    """恢复 curses 环境"""
    stdscr = curses.initscr()
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    return stdscr


def get_cookie_from_file(stdscr, y, x):
    """从文件读取 Cookie"""
    h, w = stdscr.getmaxyx()

    # 显示说明
    stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
    stdscr.addstr(y, x, "【方式一：从文件读取 Cookie】")
    stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)

    instructions = [
        "1. 将 Cookie 保存到文件: cookie.txt",
        "2. 文件放在程序同目录下",
        "3. 选择此方式自动读取",
    ]

    for i, line in enumerate(instructions):
        stdscr.addstr(y + 1 + i, x, line)

    # 检查文件是否存在
    cookie_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookie.txt")
    if os.path.exists(cookie_file):
        stdscr.addstr(y + 5, x, "✓ 发现 cookie.txt 文件")
        stdscr.addstr(y + 6, x, "按 f 从文件读取，按其他继续")
        stdscr.refresh()

        ch = stdscr.getch()
        if ch in (ord("f"), ord("F")):
            try:
                with open(cookie_file, "r", encoding="utf-8") as f:
                    cookie = f.read().strip()
                if cookie:
                    stdscr.addstr(y + 7, x, f"✓ 已读取 Cookie (前30字符): {cookie[:30]}...")
                    stdscr.refresh()
                    return cookie
            except Exception as e:
                stdscr.addstr(y + 7, x, f"✗ 读取失败: {e}")
                stdscr.refresh()
    else:
        stdscr.addstr(y + 5, x, "✗ 未发现 cookie.txt 文件")
        stdscr.refresh()

    return None


def add_account_screen(stdscr, accounts):
    """添加账户界面"""
    h, w = stdscr.getmaxyx()
    stdscr.clear()

    title = "添加账户"
    title_x = max(0, (w - len(title)) // 2)
    stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, title_x, title)
    stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

    x = max(2, (w - 55) // 2)

    # 方式一：从文件读取
    cookie_str = get_cookie_from_file(stdscr, 3, x)
    if cookie_str:
        # 标签输入
        label = get_input(stdscr, "请输入标签 (可选):", 12, x)
        if label is None:
            label = ""

        # 验证中提示
        stdscr.addstr(16, x, "正在验证 Cookie...")
        stdscr.refresh()

        # 验证 cookie
        user_info = validate_cookie(cookie_str)
        if not user_info:
            stdscr.addstr(18, x, "验证失败！Cookie 无效或网络错误")
            stdscr.addstr(20, x, "按任意键返回...")
            stdscr.getch()
            return False

        # 检查是否已存在
        for acc in accounts:
            if acc.get("cookie") == cookie_str:
                stdscr.addstr(18, x, "该账户已存在！")
                stdscr.addstr(20, x, "按任意键返回...")
                stdscr.getch()
                return False

        # 添加账户
        account = {
            "cookie": cookie_str,
            "token": user_info.get("token", ""),
            "user_id": user_info["user_id"],
            "user_name": user_info["user_name"],
            "label": label,
            "is_active": True,
            "added_at": datetime.now().isoformat(),
        }
        accounts.append(account)
        save_accounts(accounts)

        stdscr.addstr(18, x, f"添加成功！用户: {user_info['user_name']}")
        stdscr.addstr(20, x, "按任意键返回...")
        stdscr.getch()
        return True

    # 方式二：手动输入
    stdscr.clear()
    stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, title_x, title)
    stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

    stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
    stdscr.addstr(3, x, "【获取 Cookie 步骤】")
    stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)

    instructions = [
        "1. 打开浏览器访问 https://chat.z.ai",
        "2. 登录您的 Z.ai 账户",
        "3. 按 F12 打开开发者工具",
        "4. 切换到 Network (网络) 选项卡",
        "5. 刷新页面，找到任意请求",
        "6. 在 Headers 中找到 Cookie 字段",
        "7. 复制完整的 Cookie 值",
    ]

    for i, line in enumerate(instructions):
        stdscr.addstr(4 + i, x, line)

    stdscr.addstr(12, x, "─" * 50)

    # Cookie 输入
    stdscr.addstr(14, x, "请粘贴 Cookie:")
    stdscr.addstr(15, x, "(支持 Ctrl+V 粘贴)")
    stdscr.refresh()

    # 使用 Python 的 input 函数获取（更可靠的粘贴支持）
    curses.endwin()
    print("\n" + "=" * 60)
    print("请粘贴 Cookie (粘贴后按 Enter):")
    print("=" * 60)
    cookie_str = input().strip()

    if not cookie_str:
        print("未输入 Cookie，返回...")
        return False

    print(f"\n已接收 Cookie (前30字符): {cookie_str[:30]}...")
    print("正在验证...")
    print("=" * 60)

    # 恢复 curses
    stdscr = curses.initscr()
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)

    # 标签输入
    label = get_input(stdscr, "请输入标签 (可选):", 18, x)
    if label is None:
        label = ""

    # 验证中提示
    stdscr.addstr(22, x, "正在验证 Cookie...")
    stdscr.refresh()

    # 验证 cookie
    user_info = validate_cookie(cookie_str)
    if not user_info:
        stdscr.addstr(24, x, "验证失败！Cookie 无效或网络错误")
        stdscr.addstr(26, x, "按任意键返回...")
        stdscr.getch()
        return False

    # 检查是否已存在
    for acc in accounts:
        if acc.get("cookie") == cookie_str:
            stdscr.addstr(24, x, "该账户已存在！")
            stdscr.addstr(26, x, "按任意键返回...")
            stdscr.getch()
            return False

    # 添加账户
    account = {
        "cookie": cookie_str,
        "token": user_info.get("token", ""),
        "user_id": user_info["user_id"],
        "user_name": user_info["user_name"],
        "label": label,
        "is_active": True,
        "added_at": datetime.now().isoformat(),
    }
    accounts.append(account)
    save_accounts(accounts)

    stdscr.addstr(24, x, f"添加成功！用户: {user_info['user_name']}")
    stdscr.addstr(26, x, "按任意键返回...")
    stdscr.getch()
    return True


def delete_account(stdscr, accounts, idx):
    """删除账户"""
    if idx < 0 or idx >= len(accounts):
        return False

    h, w = stdscr.getmaxyx()
    acc = accounts[idx]
    name = acc.get("user_name", "未知")

    stdscr.clear()
    title = "确认删除"
    title_x = max(0, (w - len(title)) // 2)
    stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, title_x, title)
    stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

    x = max(2, (w - 50) // 2)
    stdscr.addstr(3, x, f"确定要删除账户 '{name}' 吗?")
    stdscr.addstr(5, x, "按 y 确认，按其他键取消")
    stdscr.refresh()

    ch = stdscr.getch()
    if ch in (ord("y"), ord("Y")):
        accounts.pop(idx)
        save_accounts(accounts)
        return True
    return False


def edit_account_screen(stdscr, accounts, idx):
    """编辑账户标签"""
    if idx < 0 or idx >= len(accounts):
        return False

    h, w = stdscr.getmaxyx()
    acc = accounts[idx]

    stdscr.clear()
    title = "编辑账户"
    title_x = max(0, (w - len(title)) // 2)
    stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, title_x, title)
    stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

    x = max(2, (w - 50) // 2)
    stdscr.addstr(3, x, f"用户: {acc.get('user_name', '未知')}")
    stdscr.addstr(4, x, f"当前标签: {acc.get('label', '无')}")

    label = get_input(stdscr, "输入新标签 (留空清除):", 6, x)
    if label is None:
        return False

    acc["label"] = label
    save_accounts(accounts)

    stdscr.addstr(10, x, "编辑成功！")
    stdscr.addstr(12, x, "按任意键返回...")
    stdscr.getch()
    return True


def account_list_screen(stdscr, accounts):
    """账户列表界面"""
    current_idx = 0
    scroll_offset = 0

    while True:
        h, w = stdscr.getmaxyx()
        max_display = h - 5

        # 调整滚动
        if current_idx < scroll_offset:
            scroll_offset = current_idx
        elif current_idx >= scroll_offset + max_display:
            scroll_offset = current_idx - max_display + 1

        draw_account_list(stdscr, accounts, current_idx, scroll_offset)

        ch = stdscr.getch()
        if ch == ord("q") or ch == ord("Q"):
            break
        elif ch == curses.KEY_UP:
            current_idx = max(0, current_idx - 1)
        elif ch == curses.KEY_DOWN:
            current_idx = min(len(accounts) - 1, current_idx + 1) if accounts else 0
        elif ch == 10:  # Enter - 切换账户启用状态
            if accounts and 0 <= current_idx < len(accounts):
                acc = accounts[current_idx]
                acc["is_active"] = not acc.get("is_active", True)
                save_accounts(accounts)
        elif ch == ord("a") or ch == ord("A"):
            add_account_screen(stdscr, accounts)
        elif ch == ord("b") or ch == ord("B"):
            batch_import_screen(stdscr, accounts)
        elif ch == ord("d") or ch == ord("D"):
            if accounts and 0 <= current_idx < len(accounts):
                if delete_account(stdscr, accounts, current_idx):
                    if current_idx >= len(accounts) and accounts:
                        current_idx = len(accounts) - 1
        elif ch == ord("e") or ch == ord("E"):
            if accounts and 0 <= current_idx < len(accounts):
                edit_account_screen(stdscr, accounts, current_idx)


def main_menu(stdscr):
    """主菜单"""
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)

    accounts = load_accounts()
    current_idx = 0

    menu_options = [
        "查看账户列表",
        "添加账户",
        "批量导入",
        "退出",
    ]

    while True:
        draw_menu(stdscr, "Z.ai 账户管理器", menu_options, current_idx)

        ch = stdscr.getch()
        if ch == ord("q") or ch == ord("Q"):
            break
        elif ch == curses.KEY_UP:
            current_idx = max(0, current_idx - 1)
        elif ch == curses.KEY_DOWN:
            current_idx = min(len(menu_options) - 1, current_idx + 1)
        elif ch == 10:  # Enter
            if current_idx == 0:  # 查看账户列表
                account_list_screen(stdscr, accounts)
            elif current_idx == 1:  # 添加账户
                add_account_screen(stdscr, accounts)
            elif current_idx == 2:  # 批量导入
                batch_import_screen(stdscr, accounts)
            elif current_idx == 3:  # 退出
                break


def main():
    """主函数"""
    try:
        curses.wrapper(main_menu)
    except KeyboardInterrupt:
        pass
    print("已退出账户管理器")


if __name__ == "__main__":
    main()
