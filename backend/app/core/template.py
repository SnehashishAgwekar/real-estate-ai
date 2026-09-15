# ============================================================
# template.py
# ============================================================
# ONLY message templates live in this file.
# No API calls here.
# ============================================================


# ============================================================
# SMS TEMPLATE
# ============================================================

def broker_interest_sms(
    user_name: str,
    property_name: str,
    user_phone: str,
) -> str:

    return (
        f"NEW PROPERTY INTEREST\n"
        f"User: {user_name}\n"
        f"Property: {property_name}\n"
        f"Contact: {user_phone}\n"
        f"Please contact the customer."
    )


# ============================================================
# WHATSAPP - PROPERTY ALERT
# ============================================================

def broker_property_whatsapp(
    property_name: str,
    location: str,
    price: str,
    area: str,
) -> str:

    return f"""✨ *NEW PROPERTY ALERT* ✨

━━━━━━━━━━━━━━━━━━
🏡 *{property_name}*

📍 *Location*
   {location}

💰 *Price*
   {price}

📐 *Area*
   {area}
━━━━━━━━━━━━━━━━━━

🏠 *Make this beautiful home yours!*

Interested in this property?

Reply *INTERESTED* and our
property consultant will contact
you shortly.

📞 We look forward to helping you
find your perfect home!

━━━━━━━━━━━━━━━━━━
"""


# ============================================================
# WHATSAPP - BROKER INTEREST NOTIFICATION
# ============================================================

def broker_interest_whatsapp(
    user_name: str,
    property_name: str,
    user_phone: str,
) -> str:

    return f"""🔔 *NEW PROPERTY INTEREST*

━━━━━━━━━━━━━━━━━━

👤 *Customer*
{user_name}

🏠 *Property*
{property_name}

📞 *Contact*
{user_phone}

━━━━━━━━━━━━━━━━━━

The customer is interested in this property.

Please contact them as soon as possible.
"""


# ============================================================
# EMAIL TEMPLATE
# ============================================================

def broker_interest_email(
    user_name: str,
    property_name: str,
    user_phone: str,
) -> str:

    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">

    <style>

        body {{
            font-family: Arial, Helvetica, sans-serif;
            background-color: #f4f6f8;
            margin: 0;
            padding: 30px;
        }}

        .container {{
            max-width: 600px;
            margin: auto;
            background: white;
            border-radius: 12px;
            padding: 30px;
        }}

        .header {{
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 20px;
        }}

        .property {{
            background-color: #f7f7f7;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }}

        .row {{
            margin: 12px 0;
            font-size: 16px;
        }}

        .label {{
            font-weight: bold;
        }}

        .contact {{
            background-color: #eef7ff;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
        }}

        .footer {{
            color: #777;
            font-size: 13px;
            margin-top: 25px;
        }}

    </style>
</head>

<body>

<div class="container">

    <div class="header">
        🔔 New Property Interest
    </div>

    <p>
        A customer has shown interest in one of your properties.
    </p>

    <div class="property">

        <div class="row">
            <span class="label">👤 Customer:</span>
            {user_name}
        </div>

        <div class="row">
            <span class="label">🏠 Property:</span>
            {property_name}
        </div>

        <div class="row">
            <span class="label">📞 Contact:</span>
            {user_phone}
        </div>

    </div>

    <div class="contact">

        <strong>Action Required</strong>

        <p>
            Please contact the customer regarding their
            interest in the property.
        </p>

    </div>

    <div class="footer">
        This notification was automatically generated
        by the Real Estate AI system.
    </div>

</div>

</body>
</html>
"""


# ============================================================
# SMS TEMPLATE - BUYER CONFIRMATION
# ============================================================

def buyer_interest_confirmation_sms(
    property_name: str,
    broker_name: str,
    broker_phone: str,
    broker_email: str,
) -> str:
    """SMS sent to the buyer after they tap 'Interested', confirming the broker was notified."""

    contact_line = broker_phone
    if broker_email:
        contact_line = f"{broker_phone} / {broker_email}"

    return (
        f"CASIVA: Your interest in \"{property_name}\" has been sent to "
        f"{broker_name}. "
        f"Reach them at {contact_line}."
    )
