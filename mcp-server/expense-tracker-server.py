from datetime import date
from fastmcp import FastMCP
from db.connection import get_connection

mcp = FastMCP(name="Expense Tracker")


@mcp.tool()
def add_expense(amount: float, category: str, description: str, transaction_date: date | None = None) -> str:
    """Add a new expense."""
    if amount <= 0:
        return "Error: amount must be greater than 0."
    if transaction_date is None:
        transaction_date = date.today()
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO transactions
                    (amount, category, description, transaction_type, transaction_date)
                VALUES
                    (%s, %s, %s, 'expense', %s)
                RETURNING id;
                """,
                (amount, category, description, transaction_date),
            )
            transaction_id = cursor.fetchone()[0]
        conn.commit()

        return (
            f"Expense added successfully. "
            f"Transaction ID: {transaction_id}, "
            f"Amount: ₹{amount:.2f}, "
            f"Category: {category}, "
            f"Date: {transaction_date}"
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@mcp.tool()
def list_expenses(from_date: date, to_date: date) -> str:
    """List expenses between two dates."""
    if from_date > to_date:
        return "Error: from_date cannot be later than to_date."
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, amount, category, description, transaction_date
                FROM transactions
                WHERE transaction_type = 'expense'
                  AND transaction_date BETWEEN %s AND %s
                ORDER BY transaction_date DESC, id DESC;
                """,
                (from_date, to_date),
            )
            expenses = cursor.fetchall()
        if not expenses:
            return f"No expenses found between {from_date} and {to_date}."
        result = [
            f"Expenses from {from_date} to {to_date}:",
            "",
        ]
        total = 0
        for expense in expenses:
            (
                transaction_id,
                amount,
                category,
                description,
                transaction_date,
            ) = expense
            total += float(amount)
            result.append(
                f"ID: {transaction_id} | "
                f"₹{amount:.2f} | "
                f"{category} | "
                f"{description} | "
                f"{transaction_date}"
            )
        result.append("")
        result.append(f"Total expenses: ₹{total:.2f}")
        return "\n".join(result)
    finally:
        conn.close()
@mcp.tool()
def summarize_expenses(from_date: date, to_date: date) -> str:
    """Summarize expenses between two dates."""
    if from_date > to_date:
        return "Error: from_date cannot be later than to_date."
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(amount), 0)
                FROM transactions
                WHERE transaction_type = 'expense'
                  AND transaction_date BETWEEN %s AND %s;
                """,
                (from_date, to_date),
            )

            count, total = cursor.fetchone()

            cursor.execute(
                """
                SELECT category, SUM(amount)
                FROM transactions
                WHERE transaction_type = 'expense'
                  AND transaction_date BETWEEN %s AND %s
                GROUP BY category
                ORDER BY SUM(amount) DESC;
                """,
                (from_date, to_date),
            )

            category_totals = cursor.fetchall()

        result = [
            "Expense Summary",
            "----------------",
            f"Period: {from_date} to {to_date}",
            "",
            f"Total expenses: ₹{total:.2f}",
            f"Number of expenses: {count}",
        ]

        if category_totals:
            result.append("")
            result.append("By category:")

            for category, category_total in category_totals:
                result.append(
                    f"{category}: ₹{category_total:.2f}"
                )

        return "\n".join(result)

    finally:
        conn.close()

@mcp.tool()
def edit_expense(
    transaction_id: int,
    amount: float | None = None,
    category: str | None = None,
    description: str | None = None,
    transaction_date: date | None = None,
) -> str:
    """Edit an existing expense."""

    if amount is not None and amount <= 0:
        return "Error: amount must be greater than 0."

    if (
        amount is None
        and category is None
        and description is None
        and transaction_date is None
    ):
        return "Error: provide at least one field to update."

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, amount, category, description, transaction_date
                FROM transactions
                WHERE id = %s
                  AND transaction_type = 'expense';
                """,
                (transaction_id,),
            )

            existing_expense = cursor.fetchone()

            if existing_expense is None:
                return (
                    f"Error: expense with ID "
                    f"{transaction_id} not found."
                )

            current_amount = existing_expense[1]
            current_category = existing_expense[2]
            current_description = existing_expense[3]
            current_date = existing_expense[4]

            new_amount = (
                amount
                if amount is not None
                else current_amount
            )

            new_category = (
                category
                if category is not None
                else current_category
            )

            new_description = (
                description
                if description is not None
                else current_description
            )

            new_date = (
                transaction_date
                if transaction_date is not None
                else current_date
            )

            cursor.execute(
                """
                UPDATE transactions
                SET amount = %s,
                    category = %s,
                    description = %s,
                    transaction_date = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                  AND transaction_type = 'expense';
                """,
                (
                    new_amount,
                    new_category,
                    new_description,
                    new_date,
                    transaction_id,
                ),
            )

        conn.commit()

        return (
            f"Expense ID {transaction_id} updated successfully.\n"
            f"Amount: ₹{new_amount:.2f}\n"
            f"Category: {new_category}\n"
            f"Description: {new_description}\n"
            f"Date: {new_date}"
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


@mcp.tool()
def delete_expense(transaction_id: int) -> str:
    """Delete an existing expense."""

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, amount, category, description, transaction_date
                FROM transactions
                WHERE id = %s
                  AND transaction_type = 'expense';
                """,
                (transaction_id,),
            )

            expense = cursor.fetchone()

            if expense is None:
                return (
                    f"Error: expense with ID "
                    f"{transaction_id} not found."
                )

            (
                expense_id,
                amount,
                category,
                description,
                transaction_date,
            ) = expense

            cursor.execute(
                """
                DELETE FROM transactions
                WHERE id = %s
                  AND transaction_type = 'expense';
                """,
                (transaction_id,),
            )

        conn.commit()

        return (
            "Expense deleted successfully.\n"
            f"Transaction ID: {expense_id}\n"
            f"Amount: ₹{amount:.2f}\n"
            f"Category: {category}\n"
            f"Description: {description}\n"
            f"Date: {transaction_date}"
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


@mcp.tool()
def credit(
    amount: float,
    category: str,
    description: str,
    transaction_date: date | None = None,
) -> str:
    """Add an income or credit transaction."""

    if amount <= 0:
        return "Error: amount must be greater than 0."

    if transaction_date is None:
        transaction_date = date.today()

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO transactions
                    (amount, category, description, transaction_type, transaction_date)
                VALUES
                    (%s, %s, %s, 'credit', %s)
                RETURNING id;
                """,
                (
                    amount,
                    category,
                    description,
                    transaction_date,
                ),
            )

            transaction_id = cursor.fetchone()[0]

        conn.commit()

        return (
            f"Credit added successfully. "
            f"Transaction ID: {transaction_id}, "
            f"Amount: ₹{amount:.2f}, "
            f"Category: {category}, "
            f"Date: {transaction_date}"
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    mcp.run()