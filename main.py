import json
import os
from random import randint
import time
import pyfiglet
from dotenv import load_dotenv
from rich import print
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from groq import Groq

trIDS = {}
filename = "FinanceTracker/transactions.json"
advice_log_file = "FinanceTracker/ai_coaching_history.txt"
console = Console()
BUDGET_LIMIT = 5000.00

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def show_welcome_banner():
    ascii_banner = pyfiglet.figlet_format("Finance Tracker", font="slant")
    console.print(f"[bold green]{ascii_banner}[/bold green]")
    console.print(
        " :money_with_wings: [bold white]Be smart with your expenses![/bold white] :money_with_wings:\n"
    )
    console.print(
        f"[dim white]Current Safety Budget Threshold Limit: [/dim white][bold cyan]₹{BUDGET_LIMIT:,.2f}[/bold cyan]"
    )
    console.print(
        "[dim green]==================================================[/dim green]\n"
    )


def rand_trID() -> int:
    trID = ""
    for _ in range(6):
        trID += str(randint(0, 9))
    return int(trID)


def get_ai_suggestion(transactions, above_budget_limit):
    """
    Sends the transactions to Groq and prints a rich animation while waiting.
    """
    system_prompt = f"""You are a direct, empathetic, and highly strategic AI Financial Coach. Your mission is to audit batches of transaction data, expose hidden spending patterns, and help users eliminate mindless expenses.

You will receive input as a list containing multiple transaction objects in this format:
[
  {{
    "series": number,
    "trName": transaction_name,
    "trExp": transaction_exp,
    "trReason": transaction_reason,
    "trId": trID
  }},
  ...
]

Is above budget limit: {above_budget_limit}

CRITICAL EXECUTION RULES:
1. Ignore "series" and "trId" for every transaction. They are irrelevant metadata.
2. Analyze the aggregate data using "trName", "trExp", and "trReason". 
3. Group repetitive transactions (e.g., multiple coffee runs, frequent food deliveries, or overlapping streaming services) to show the user the compounding total cost.
4. Call out the "mindless expenses"—purchases made out of convenience, fatigue, impulse, or poor planning based on the "trReason" fields.
5. Provide high-impact, actionable advice to cut these expenses immediately. Offer realistic lifestyle swaps and concrete habit changes.
6. Acknowledge directly if the person is above their budget threshold limit based on the provided condition.

OUTPUT FORMAT:
Deliver your advice in a clean, highly scannable, conversational format. Keep it punchy and motivating. Use these exact sections:

### 📊 The Big Picture
* [Highlight the total financial leakage from these combined transactions.]
* [Identify the single biggest category of mindless spending found in this batch.]

### 🛑 Mindless Spending Triggers
* **[Pattern 1]:** [Brief critique of the mindset behind these specific transactions.]
* **[Pattern 2]:** [Brief critique of any passive or recurring leakage found.]

### 💡 Your Action Plan to Cut Costs
* [Actionable step 1]
* [Actionable step 2]

### 💰 Potential Monthly Savings
[An encouraging estimation of how much money they will claw back.]"""

    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[bold cyan]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Analyzing your spending habits with Groq AI...", total=None)
        
        try:
            chat_completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(transactions)}
                ]
            )
            advice_text = chat_completion.choices[0].message.content
            
                
            return advice_text
            
        except Exception as e:
            return f"[bold red]Failed to fetch AI Advice: {str(e)}[/bold red]"


def add_transaction(transaction: tuple) -> None:
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        with open(filename, "r") as file:
            data_list = json.load(file)
    else:
        data_list = []

    transaction_name = transaction[0]
    transaction_exp = transaction[1]
    transaction_reason = transaction[2]
    trID = rand_trID()

    series_number = len(data_list) + 1

    data_list.append(
        {
            "series": series_number,
            "trName": transaction_name,
            "trExp": transaction_exp,
            "trReason": transaction_reason,
            "trId": trID,
        }
    )

    with open(filename, "w") as file:
        json.dump(data_list, file, indent=4)

    trIDS[transaction] = trID
    
    # Invalidate cached advice when adding data
    if os.path.exists(advice_log_file + ".cached"):
        os.remove(advice_log_file + ".cached")


def delete_transaction(trID: int) -> None:
    if not os.path.exists(filename):
        return

    with open(filename, "r") as file:
        line = json.load(file)

    found = False
    for i in line:
        if i["trId"] == trID:
            line.remove(i)
            found = True
            break

    for index, item in enumerate(line):
        item["series"] = index + 1

    with open(filename, "w") as file:
        json.dump(line, file, indent=4)
        
    # Invalidate cached advice when deleting data
    if found and os.path.exists(advice_log_file + ".cached"):
        os.remove(advice_log_file + ".cached")


def clear_all_transactions() -> None:
    if os.path.exists(filename):
        with open(filename, "w") as file:
            json.dump([], file, indent=4)
    if os.path.exists(advice_log_file + ".cached"):
        os.remove(advice_log_file + ".cached")


def show_transactions(filter_keyword: str = None):
    if not os.path.exists(filename) or os.path.getsize(filename) == 0:
        console.print(
            "\n[bold yellow]⚠️ No recorded transactions found.[/bold yellow]\n"
        )
        return

    with open(filename, "r") as file:
        transactions = json.load(file)

    total_cost = 0.0
    for i in transactions:
        try:
            total_cost += float(i["trExp"])
        except ValueError:
            pass

    # Budget limit styling conditions
    is_above_budget = total_cost > BUDGET_LIMIT
    if is_above_budget:
        footer_style = "blink bold red"
        title_tag = f" [bold red]⚠️ BUDGET SURPASSED BY ₹{(total_cost - BUDGET_LIMIT):,.2f}! ⚠️[/bold red]"
    else:
        footer_style = "bold green"
        title_tag = f" [bold green]👍 Within Safe Budget Boundaries (₹{(BUDGET_LIMIT - total_cost):,.2f} left)[/bold green]"

    table = Table(
        title=f"Your Current Expenses |{title_tag}",
        header_style="bold magenta",
        expand=True,
    )

    table.add_column("#", justify="center", style="dim cyan", max_width=6)
    table.add_column(
        "Transaction Name",
        justify="left",
        style="white",
        footer="[bold magenta]Total Spending[/bold magenta]",
    )
    table.add_column(
        "Cost",
        justify="right",
        style="bold green",
        footer=f"[{footer_style}]₹{total_cost:,.2f}[/{footer_style}]",
    )
    table.add_column("Reason for Expense", justify="left", style="yellow")
    table.add_column("ID", justify="center", style="dim white")

    visible_rows = 0
    for i in transactions:
        if filter_keyword and filter_keyword not in i["trName"].lower():
            continue

        visible_rows += 1
        try:
            cost_val = f"₹{float(i['trExp']):,.2f}"
        except ValueError:
            cost_val = f"₹{i['trExp']}"

        table.add_row(
            str(i["series"]),
            i["trName"],
            cost_val,
            i["trReason"],
            str(i["trId"])
        )

    if visible_rows == 0 and filter_keyword:
        console.print(
            f"\n[bold yellow]🔍 No transactions matching '{filter_keyword}' found.[/bold yellow]\n"
        )
        return

    print("\n")
    console.print(table)
    print("\n")
    
    console.print("[bold purple]🤖 AI Coach Analysis:[/bold purple]")
    
    # Check if advice cache exists to prevent unneeded API hits
    cache_path = advice_log_file + ".cached"
    if not filter_keyword and os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as cf:
            ai_advice = cf.read()
    else:
        ai_advice = get_ai_suggestion(transactions, is_above_budget)

    console.print(ai_advice)
    print("\n" + "="*50 + "\n")


def run_tracker():
    show_welcome_banner()

    while True:
        console.print(
            "[bold cyan]What operation would you like to perform:[/bold cyan]"
        )
        console.print("1. + Add expense")
        console.print("2. - Remove expense")
        console.print("3. :bar_chart: Show expense")
        console.print("4. :mag: Filter/Search expenses by name")
        console.print("5. :wastebasket: Clear entire history")
        console.print("6. :door: Exit Program")

        try:
            userinput = int(input("\nEnter option number (1-6): "))
        except ValueError:
            console.print("[bold red]Invalid selection! Please input a valid option number.[/bold red]\n")
            continue

        if userinput == 1:
            name = input("Name of expense : ")
            while True:
                cost = input("Cost of expense : ")
                try:
                    float(cost)
                    break
                except ValueError:
                    console.print("[bold red]Please enter a numeric cost value.[/bold red]")
            reason = input("Reason for expense : ")
            add_transaction((name, cost, reason))
            console.print("[bold green]✔ Expense successfully added![/bold green]\n")

        elif userinput == 2:
            try:
                id_to_del = int(input("Enter the transaction ID to remove: "))
                delete_transaction(id_to_del)
                console.print("[bold green]✔ Processed transaction deletion request.[/bold green]\n")
            except ValueError:
                console.print("[bold red]Invalid ID format.[/bold red]\n")

        elif userinput == 3:
            show_transactions()

        elif userinput == 4:
            keyword = input("Enter search keyword: ").lower()
            show_transactions(filter_keyword=keyword)

        elif userinput == 5:
            confirm = input("Are you sure you want to clear your entire tracking history? (y/n): ").lower()
            if confirm == 'y':
                clear_all_transactions()
                console.print("[bold green]✔ Complete financial tracker history cleared![/bold green]\n")

        elif userinput == 6:
            console.print("[bold yellow]Goodbye! Keep saving money.[/bold yellow]")
            print("Made with love by Vidhan")
            break

if __name__ == "__main__":
    run_tracker()
