"""
HTML templates for different UI types.
"""

import random
from typing import Any

from evaluation.synthetic_ui.components import BoundingBox, SemanticAnchor, SyntheticUIComponent, SyntheticUIInteraction
from evaluation.synthetic_ui.config import ElementType


def get_color_palette(rng: random.Random | None = None) -> dict[str, str]:
    if rng is None:
        rng = random.Random()
    palettes = [
        {
            "primary": "#3B82F6",
            "secondary": "#8B5CF6",
            "background": "#FFFFFF",
            "text": "#1F2937",
            "border": "#E5E7EB",
        },
        {
            "primary": "#10B981",
            "secondary": "#3B82F6",
            "background": "#F9FAFB",
            "text": "#111827",
            "border": "#D1D5DB",
        },
        {
            "primary": "#EF4444",
            "secondary": "#F59E0B",
            "background": "#FFFFFF",
            "text": "#374151",
            "border": "#9CA3AF",
        },
        {
            "primary": "#8B5CF6",
            "secondary": "#EC4899",
            "background": "#FAFAFA",
            "text": "#0F172A",
            "border": "#CBD5E1",
        },
    ]
    return rng.choice(palettes)


def generate_login_form_html(colors: dict[str, str]) -> tuple[str, list[SyntheticUIComponent], list[SyntheticUIInteraction], list[SemanticAnchor]]:
    components = []
    interactions = []
    anchors = []

    username_comp = SyntheticUIComponent.create(
        element_type=ElementType.INPUT,
        text="",
        bounding_box=BoundingBox(400, 250, 480, 40),
        interactive=True,
        action="type",
        semantic_role="username_input",
        anchor_text="Username",
        metadata={"placeholder": "Enter username"},
    )
    components.append(username_comp)
    interactions.append(
        SyntheticUIInteraction(
            component_id=username_comp.component_id,
            description="Enter username",
            expected_action="type",
            anchor_text="Username",
        )
    )
    anchors.append(
        SemanticAnchor(
            component_id=username_comp.component_id,
            label="username_field",
            hints=["username", "email", "login"],
        )
    )

    password_comp = SyntheticUIComponent.create(
        element_type=ElementType.INPUT,
        text="",
        bounding_box=BoundingBox(400, 310, 480, 40),
        interactive=True,
        action="type",
        semantic_role="password_input",
        anchor_text="Password",
        metadata={"placeholder": "Enter password", "input_type": "password"},
    )
    components.append(password_comp)
    interactions.append(
        SyntheticUIInteraction(
            component_id=password_comp.component_id,
            description="Enter password",
            expected_action="type",
            anchor_text="Password",
        )
    )
    anchors.append(
        SemanticAnchor(
            component_id=password_comp.component_id,
            label="password_field",
            hints=["password", "pass", "secret"],
        )
    )

    submit_comp = SyntheticUIComponent.create(
        element_type=ElementType.BUTTON,
        text="Sign In",
        bounding_box=BoundingBox(400, 370, 480, 45),
        interactive=True,
        action="click",
        semantic_role="submit_button",
        anchor_text="Sign In",
    )
    components.append(submit_comp)
    interactions.append(
        SyntheticUIInteraction(
            component_id=submit_comp.component_id,
            description="Click to sign in",
            expected_action="click",
            anchor_text="Sign In",
        )
    )
    anchors.append(
        SemanticAnchor(
            component_id=submit_comp.component_id,
            label="submit_button",
            hints=["submit", "login", "sign in"],
        )
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login Form</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: {colors['background']};
            color: {colors['text']};
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }}
        .login-container {{
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            width: 480px;
        }}
        h1 {{ text-align: center; margin-bottom: 30px; color: {colors['primary']}; }}
        .form-group {{ margin-bottom: 20px; }}
        label {{ display: block; margin-bottom: 8px; font-weight: 500; }}
        input {{
            width: 100%;
            padding: 12px;
            border: 1px solid {colors['border']};
            border-radius: 4px;
            font-size: 14px;
        }}
        input:focus {{ outline: none; border-color: {colors['primary']}; }}
        button {{
            width: 100%;
            padding: 12px;
            background: {colors['primary']};
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
        }}
        button:hover {{ opacity: 0.9; }}
    </style>
</head>
<body>
    <div class="login-container">
        <h1>Welcome Back</h1>
        <form>
            <div class="form-group">
                <label for="{username_comp.component_id}">Username</label>
                <input type="text" id="{username_comp.component_id}" placeholder="Enter username">
            </div>
            <div class="form-group">
                <label for="{password_comp.component_id}">Password</label>
                <input type="password" id="{password_comp.component_id}" placeholder="Enter password">
            </div>
            <button type="submit" id="{submit_comp.component_id}">Sign In</button>
        </form>
    </div>
</body>
</html>"""

    return html, components, interactions, anchors


def generate_search_page_html(colors: dict[str, str]) -> tuple[str, list[SyntheticUIComponent], list[SyntheticUIInteraction], list[SemanticAnchor]]:
    components = []
    interactions = []
    anchors = []

    search_input = SyntheticUIComponent.create(
        element_type=ElementType.INPUT,
        text="",
        bounding_box=BoundingBox(350, 150, 500, 50),
        interactive=True,
        action="type",
        semantic_role="search_input",
        anchor_text="Search",
        metadata={"placeholder": "Search for anything..."},
    )
    components.append(search_input)
    interactions.append(
        SyntheticUIInteraction(
            component_id=search_input.component_id,
            description="Type search query",
            expected_action="type",
            anchor_text="Search",
        )
    )
    anchors.append(
        SemanticAnchor(
            component_id=search_input.component_id,
            label="search_input",
            hints=["search", "query", "find"],
        )
    )

    search_button = SyntheticUIComponent.create(
        element_type=ElementType.BUTTON,
        text="Search",
        bounding_box=BoundingBox(860, 150, 100, 50),
        interactive=True,
        action="click",
        semantic_role="search_button",
        anchor_text="Search",
    )
    components.append(search_button)
    interactions.append(
        SyntheticUIInteraction(
            component_id=search_button.component_id,
            description="Click to search",
            expected_action="click",
            anchor_text="Search",
        )
    )
    anchors.append(
        SemanticAnchor(
            component_id=search_button.component_id,
            label="search_button",
            hints=["search", "submit", "find"],
        )
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Search</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: {colors['background']};
            color: {colors['text']};
            padding: 20px;
        }}
        .search-container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 50px 20px;
        }}
        h1 {{ text-align: center; margin-bottom: 40px; color: {colors['primary']}; }}
        .search-box {{
            display: flex;
            gap: 10px;
            margin: 0 auto;
            max-width: 700px;
        }}
        input {{
            flex: 1;
            padding: 15px 20px;
            border: 2px solid {colors['border']};
            border-radius: 8px;
            font-size: 16px;
        }}
        input:focus {{ outline: none; border-color: {colors['primary']}; }}
        button {{
            padding: 15px 30px;
            background: {colors['primary']};
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
        }}
        button:hover {{ opacity: 0.9; }}
    </style>
</head>
<body>
    <div class="search-container">
        <h1>Find What You Need</h1>
        <div class="search-box">
            <input type="text" id="{search_input.component_id}" placeholder="Search for anything...">
            <button id="{search_button.component_id}">Search</button>
        </div>
    </div>
</body>
</html>"""

    return html, components, interactions, anchors


def generate_checkout_form_html(colors: dict[str, str]) -> tuple[str, list[SyntheticUIComponent], list[SyntheticUIInteraction], list[SemanticAnchor]]:
    components = []
    interactions = []
    anchors = []

    email_comp = SyntheticUIComponent.create(
        element_type=ElementType.INPUT,
        text="",
        bounding_box=BoundingBox(400, 150, 480, 40),
        interactive=True,
        action="type",
        semantic_role="email_input",
        anchor_text="Email",
        metadata={"placeholder": "your@email.com", "input_type": "email"},
    )
    components.append(email_comp)
    interactions.append(
        SyntheticUIInteraction(
            component_id=email_comp.component_id,
            description="Enter email address",
            expected_action="type",
            anchor_text="Email",
        )
    )
    anchors.append(
        SemanticAnchor(
            component_id=email_comp.component_id,
            label="email_field",
            hints=["email", "contact", "address"],
        )
    )

    card_comp = SyntheticUIComponent.create(
        element_type=ElementType.INPUT,
        text="",
        bounding_box=BoundingBox(400, 220, 480, 40),
        interactive=True,
        action="type",
        semantic_role="card_input",
        anchor_text="Card Number",
        metadata={"placeholder": "1234 5678 9012 3456"},
    )
    components.append(card_comp)
    interactions.append(
        SyntheticUIInteraction(
            component_id=card_comp.component_id,
            description="Enter card number",
            expected_action="type",
            anchor_text="Card Number",
        )
    )
    anchors.append(
        SemanticAnchor(
            component_id=card_comp.component_id,
            label="card_number_field",
            hints=["card", "payment", "credit"],
        )
    )

    complete_button = SyntheticUIComponent.create(
        element_type=ElementType.BUTTON,
        text="Complete Purchase",
        bounding_box=BoundingBox(400, 350, 480, 50),
        interactive=True,
        action="click",
        semantic_role="submit_button",
        anchor_text="Complete Purchase",
    )
    components.append(complete_button)
    interactions.append(
        SyntheticUIInteraction(
            component_id=complete_button.component_id,
            description="Click to complete purchase",
            expected_action="click",
            anchor_text="Complete Purchase",
        )
    )
    anchors.append(
        SemanticAnchor(
            component_id=complete_button.component_id,
            label="purchase_button",
            hints=["complete", "purchase", "buy"],
        )
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Checkout</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: {colors['background']};
            color: {colors['text']};
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }}
        .checkout-container {{
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            width: 480px;
        }}
        h1 {{ text-align: center; margin-bottom: 30px; color: {colors['primary']}; }}
        .form-group {{ margin-bottom: 20px; }}
        label {{ display: block; margin-bottom: 8px; font-weight: 500; }}
        input {{
            width: 100%;
            padding: 12px;
            border: 1px solid {colors['border']};
            border-radius: 4px;
            font-size: 14px;
        }}
        input:focus {{ outline: none; border-color: {colors['primary']}; }}
        button {{
            width: 100%;
            padding: 15px;
            background: {colors['primary']};
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 10px;
        }}
        button:hover {{ opacity: 0.9; }}
    </style>
</head>
<body>
    <div class="checkout-container">
        <h1>Checkout</h1>
        <form>
            <div class="form-group">
                <label for="{email_comp.component_id}">Email</label>
                <input type="email" id="{email_comp.component_id}" placeholder="your@email.com">
            </div>
            <div class="form-group">
                <label for="{card_comp.component_id}">Card Number</label>
                <input type="text" id="{card_comp.component_id}" placeholder="1234 5678 9012 3456">
            </div>
            <button type="submit" id="{complete_button.component_id}">Complete Purchase</button>
        </form>
    </div>
</body>
</html>"""

    return html, components, interactions, anchors


def generate_data_table_html(colors: dict[str, str]) -> tuple[str, list[SyntheticUIComponent], list[SyntheticUIInteraction], list[SemanticAnchor]]:
    components = []
    interactions = []
    anchors = []

    rows = [
        ["Alice Johnson", "alice@example.com", "Engineer"],
        ["Bob Smith", "bob@example.com", "Designer"],
        ["Carol White", "carol@example.com", "Manager"],
    ]

    y_offset = 200
    for idx, row in enumerate(rows):
        action_button = SyntheticUIComponent.create(
            element_type=ElementType.BUTTON,
            text="View",
            bounding_box=BoundingBox(1000, y_offset + idx * 60, 80, 35),
            interactive=True,
            action="click",
            semantic_role=f"view_row_{idx}",
            anchor_text=f"View {row[0]}",
        )
        components.append(action_button)
        interactions.append(
            SyntheticUIInteraction(
                component_id=action_button.component_id,
                description=f"View details for {row[0]}",
                expected_action="click",
                anchor_text="View",
            )
        )
        anchors.append(
            SemanticAnchor(
                component_id=action_button.component_id,
                label=f"view_button_{idx}",
                hints=["view", row[0].split()[0].lower(), "details"],
            )
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Table</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: {colors['background']};
            color: {colors['text']};
            padding: 40px;
        }}
        .table-container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        h1 {{ margin-bottom: 30px; color: {colors['primary']}; }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid {colors['border']};
        }}
        th {{
            background: {colors['primary']};
            color: white;
            font-weight: 600;
        }}
        button {{
            padding: 8px 16px;
            background: {colors['primary']};
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }}
        button:hover {{ opacity: 0.9; }}
    </style>
</head>
<body>
    <div class="table-container">
        <h1>Team Members</h1>
        <table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Alice Johnson</td>
                    <td>alice@example.com</td>
                    <td>Engineer</td>
                    <td><button id="{components[0].component_id}">View</button></td>
                </tr>
                <tr>
                    <td>Bob Smith</td>
                    <td>bob@example.com</td>
                    <td>Designer</td>
                    <td><button id="{components[1].component_id}">View</button></td>
                </tr>
                <tr>
                    <td>Carol White</td>
                    <td>carol@example.com</td>
                    <td>Manager</td>
                    <td><button id="{components[2].component_id}">View</button></td>
                </tr>
            </tbody>
        </table>
    </div>
</body>
</html>"""

    return html, components, interactions, anchors
