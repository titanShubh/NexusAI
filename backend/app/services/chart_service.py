"""Plotly chart generation service to visualize SQL query results."""

import base64
import io
import json
from typing import Any, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from openai import AsyncOpenAI

from app.config import get_settings

settings = get_settings()


async def determine_chart_config(
    query: str, 
    results: list[dict[str, Any]]
) -> Optional[dict[str, Any]]:
    """Use GPT-4o to analyze query and results, and return a chart configuration."""
    if not results:
        return None
        
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    # Extract keys and types from the first row
    sample_row = results[0]
    columns_info = {k: type(v).__name__ for k, v in sample_row.items()}
    
    system_prompt = (
        "You are a data visualization assistant.\n"
        "Analyze the user's business query, the available SQL result columns, and return the best chart configuration to display this data.\n"
        "Your response MUST be a JSON object and NOTHING else. Do not use markdown wraps (e.g. no ```json).\n"
        "If the data is not suitable for a chart (e.g., it contains only a single scalar value, or is a list of simple names with no metrics), return null.\n\n"
        "Supported chart types:\n"
        "- bar (for comparisons, categories vs numeric)\n"
        "- line (for time-series or trends over sequential data)\n"
        "- pie (for parts-of-a-whole, categorical distributions)\n"
        "- scatter (for relationships between two numeric columns)\n\n"
        "Required JSON Output format:\n"
        "{\n"
        "  \"chart_type\": \"bar\" | \"line\" | \"pie\" | \"scatter\",\n"
        "  \"x_column\": \"column_name_for_x_axis_or_pie_labels\",\n"
        "  \"y_column\": \"column_name_for_y_axis_or_pie_values\",\n"
        "  \"title\": \"Descriptive Chart Title\"\n"
        "}\n"
    )
    
    user_content = (
        f"Business Query: {query}\n"
        f"Columns: {json.dumps(columns_info)}\n"
        f"Data Preview (First 3 rows): {json.dumps(results[:3])}"
    )
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.0
        )
        content = (response.choices[0].message.content or "").strip()
        # Clean markdown code block if present
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()
            
        if content == "null" or not content:
            return None
            
        return json.loads(content)
    except Exception as e:
        print(f"Failed to determine chart config: {e}")
        return None


def generate_chart_base64(
    results: list[dict[str, Any]], 
    config: dict[str, Any]
) -> Optional[str]:
    """
    Generate a Plotly chart using the config, render it to PNG, 
    and return as a base64 encoded string.
    """
    try:
        df = pd.DataFrame(results)
        chart_type = config["chart_type"]
        x_col = config["x_column"]
        y_col = config["y_column"]
        title = config["title"]
        
        # Ensure column names exist in dataframe
        if x_col not in df.columns or y_col not in df.columns:
            # Try case-insensitive matching
            cols_lower = {c.lower(): c for c in df.columns}
            if x_col.lower() in cols_lower and y_col.lower() in cols_lower:
                x_col = cols_lower[x_col.lower()]
                y_col = cols_lower[y_col.lower()]
            else:
                return None

        # Build figure
        if chart_type == "bar":
            fig = px.bar(df, x=x_col, y=y_col, title=title, template="plotly_dark")
        elif chart_type == "line":
            fig = px.line(df, x=x_col, y=y_col, title=title, template="plotly_dark")
        elif chart_type == "pie":
            fig = px.pie(df, names=x_col, values=y_col, title=title, template="plotly_dark")
        elif chart_type == "scatter":
            fig = px.scatter(df, x=x_col, y=y_col, title=title, template="plotly_dark")
        else:
            return None

        # Apply dark theme styling
        fig.update_layout(
            paper_bgcolor="rgba(15, 23, 42, 0.8)",  # Tailwind slate-900 with opacity
            plot_bgcolor="rgba(15, 23, 42, 0.5)",
            font=dict(color="#f8fafc", family="Inter, sans-serif"),
            title=dict(x=0.5, font=dict(size=16, color="#f8fafc"))
        )
        
        # Write to memory buffer as PNG image
        img_bytes = fig.to_image(format="png", width=800, height=450, engine="kaleido")
        base64_str = base64.b64encode(img_bytes).decode("utf-8")
        return f"data:image/png;base64,{base64_str}"
        
    except Exception as e:
        print(f"Failed to generate base64 chart: {e}")
        return None


async def generate_dynamic_chart_base64(
    query: str,
    results: list[dict[str, Any]]
) -> Optional[str]:
    """
    Use GPT-4o to write custom Plotly visualization code based on a query and data,
    execute it dynamically, and render the resulting figure to base64 PNG.
    """
    if not results:
        return None
        
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    # 1. Preview data for the LLM
    columns_info = {k: type(v).__name__ for k, v in results[0].items()}
    preview_data = results[:5]
    
    system_prompt = (
        "You are an expert Python data visualization assistant for an Enterprise AI Platform.\n"
        "Your task is to write clean, executable Python code to generate a Plotly figure ('fig') based on a user's query and a pandas DataFrame 'df'.\n\n"
        "Rules:\n"
        "1. The DataFrame 'df' is already loaded and available in the execution environment.\n"
        "2. Do NOT import pandas or load data from files. Use the existing 'df' variable.\n"
        "3. You must import 'plotly.express as px' or 'plotly.graph_objects as go' if you use them.\n"
        "4. Your code must assign the final Plotly Figure object to the variable 'fig'. For example: 'fig = px.bar(df, ...)' or 'fig = go.Figure(...)'.\n"
        "5. Style the chart in dark mode. Set template='plotly_dark'. Use clean colors.\n"
        "6. Make sure all titles, labels, and legends are clearly set and readable.\n"
        "7. If the request cannot be visualized (e.g. the query doesn't ask for a chart, or the data has only 1 row/scalar value), return exactly: 'null'.\n"
        "8. Return ONLY the raw executable Python code. No markdown code block wraps (e.g. no ```python), no explanations, no comments.\n"
    )
    
    user_content = (
        f"Business Query: {query}\n"
        f"DataFrame Columns: {json.dumps(columns_info)}\n"
        f"DataFrame Preview (First 5 rows):\n{json.dumps(preview_data, indent=2)}"
    )
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.0
        )
        code = (response.choices[0].message.content or "").strip()
        
        # Clean markdown code block if present
        if code.startswith("```"):
            code = code.replace("```python", "").replace("```json", "").replace("```", "").strip()
            
        if code == "null" or not code:
            print("Visualizer LLM returned null or empty code.")
            return None
            
        # 2. Execute the generated code
        df = pd.DataFrame(results)
        
        local_vars = {
            "df": df,
            "px": px,
            "go": go,
            "fig": None
        }
        
        # We run the code in a controlled context
        exec(code, {}, local_vars)
        fig = local_vars.get("fig")
        
        if fig is None:
            print("Execution completed, but 'fig' variable was not assigned.")
            return None
            
        # Apply standard dark-theme styling overrides to the figure
        fig.update_layout(
            paper_bgcolor="rgba(15, 23, 42, 0.8)",  # Tailwind slate-900 with opacity
            plot_bgcolor="rgba(15, 23, 42, 0.5)",
            font=dict(color="#f8fafc", family="Inter, sans-serif"),
            title=dict(x=0.5, font=dict(size=16, color="#f8fafc"))
        )
        
        # Render to static PNG using Kaleido
        img_bytes = fig.to_image(format="png", width=800, height=450, engine="kaleido")
        base64_str = base64.b64encode(img_bytes).decode("utf-8")
        return f"data:image/png;base64,{base64_str}"
        
    except Exception as e:
        print(f"Failed to generate dynamic chart: {e}")
        return None
