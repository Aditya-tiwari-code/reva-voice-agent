import math
import re
from typing import Dict, Any, List, Optional


def calculate_emi(
    principal_lakh: float,
    tenure_years: int = 20,
    annual_interest_rate: float = 8.5
) -> Dict[str, Any]:
    """
    Computes home loan EMI strictly in Python code using standard banking formula:
    EMI = P * r * (1+r)^n / ((1+r)^n - 1)
    where:
      P = Principal in Rupees (principal_lakh * 100,000)
      r = Monthly interest rate = annual_rate / (12 * 100)
      n = Total months = tenure_years * 12
    """
    if principal_lakh <= 0 or tenure_years <= 0 or annual_interest_rate <= 0:
        return {
            "error": "Invalid inputs. Principal, tenure, and interest rate must be greater than zero.",
            "emi_monthly": 0,
            "total_interest_lakh": 0,
            "total_payment_lakh": 0
        }

    p = principal_lakh * 100000.0
    r = (annual_interest_rate / 100.0) / 12.0
    n = tenure_years * 12

    factor = math.pow(1.0 + r, n)
    emi = p * r * factor / (factor - 1.0)
    total_payment = emi * n
    total_interest = total_payment - p

    emi_round = int(round(emi))
    total_interest_lakh = round(total_interest / 100000.0, 2)
    total_payment_lakh = round(total_payment / 100000.0, 2)

    text_summary = (
        f"📊 **Home Loan EMI Calculation**:\n"
        f"• **Loan Amount**: ₹{principal_lakh:g} Lakh\n"
        f"• **Tenure**: {tenure_years} Years ({n} months)\n"
        f"• **Interest Rate**: {annual_interest_rate:g}%\n"
        f"• **Estimated Monthly EMI**: **₹{emi_round:,} / month**\n"
        f"• **Total Interest Payable**: ₹{total_interest_lakh} Lakh\n"
        f"• **Total Payment (Principal + Interest)**: ₹{total_payment_lakh} Lakh"
    )

    spoken_summary_en = (
        f"For a loan of {principal_lakh:g} lakh at {annual_interest_rate:g} percent for {tenure_years} years, "
        f"your estimated monthly EMI will be approximately {emi_round:,} rupees. Would you like to check eligibility?"
    )

    spoken_summary_hi = (
        f"{principal_lakh:g} लाख रुपये के लोन पर {tenure_years} साल के लिए {annual_interest_rate:g} प्रतिशत की दर से "
        f"आपकी अनुमानित मासिक ईएमआई लगभग {emi_round:,} रुपये होगी। क्या आप बैंक लोन सहायता चाहते हैं?"
    )

    return {
        "principal_lakh": principal_lakh,
        "tenure_years": tenure_years,
        "annual_interest_rate": annual_interest_rate,
        "emi_monthly": emi_round,
        "total_interest_lakh": total_interest_lakh,
        "total_payment_lakh": total_payment_lakh,
        "text_summary": text_summary,
        "spoken_summary_en": spoken_summary_en,
        "spoken_summary_hi": spoken_summary_hi
    }


def estimate_affordability(
    monthly_income: float,
    existing_emis: float = 0.0,
    down_payment_lakh: float = 0.0,
    tenure_years: int = 20,
    interest_rate: float = 8.5
) -> Dict[str, Any]:
    """
    Estimates comfortable home budget range based on standard 40-50% FOIR (Fixed Obligation to Income Ratio).
    Computed strictly in Python code.
    Clearly labeled as an informative estimate, not formal financial advice.
    """
    if monthly_income <= 0:
        return {"error": "Monthly income must be greater than zero."}

    # Available income for new EMI (standard 45% FOIR cap)
    disposable_for_emi = max(0.0, (monthly_income * 0.45) - existing_emis)
    if disposable_for_emi <= 1000:
        return {
            "comfortable_budget_lakh": round(down_payment_lakh, 2),
            "max_affordable_emi": int(disposable_for_emi),
            "message": "Existing EMIs take up most of the recommended 45% income limit."
        }

    r = (interest_rate / 100.0) / 12.0
    n = tenure_years * 12
    factor = math.pow(1.0 + r, n)

    # Max loan principal possible with this EMI
    # P = EMI * (factor - 1) / (r * factor)
    max_loan_rupees = disposable_for_emi * (factor - 1.0) / (r * factor)
    max_loan_lakh = round(max_loan_rupees / 100000.0, 2)

    total_property_budget_min = round(down_payment_lakh + (max_loan_lakh * 0.85), 1)
    total_property_budget_max = round(down_payment_lakh + max_loan_lakh, 1)

    text_summary = (
        f"💡 **Home Affordability Estimate** *(Informative rough estimate, not financial advice)*:\n"
        f"• **Monthly Income**: ₹{int(monthly_income):,}\n"
        f"• **Recommended Max Monthly EMI (45% FOIR)**: ₹{int(disposable_for_emi):,}\n"
        f"• **Estimated Loan Eligibility**: ₹{max_loan_lakh} Lakh (at {interest_rate}% for {tenure_years} yrs)\n"
        f"• **Down Payment Available**: ₹{down_payment_lakh:g} Lakh\n"
        f"• **Recommended Property Price Range**: **₹{total_property_budget_min} Lakh — ₹{total_property_budget_max} Lakh**"
    )

    spoken_en = (
        f"Based on your income, a comfortable property budget would be between {total_property_budget_min} and "
        f"{total_property_budget_max} lakh, with an EMI of around {int(disposable_for_emi):,} rupees per month."
    )

    spoken_hi = (
        f"आपकी मासिक आय के अनुसार, {total_property_budget_min} से {total_property_budget_max} लाख रुपये तक का बजट आपके लिए आरामदायक रहेगा, "
        f"जिसमें मासिक ईएमआई लगभग {int(disposable_for_emi):,} रुपये बनेगी।"
    )

    return {
        "monthly_income": monthly_income,
        "existing_emis": existing_emis,
        "down_payment_lakh": down_payment_lakh,
        "max_recommended_emi": int(disposable_for_emi),
        "estimated_loan_lakh": max_loan_lakh,
        "budget_range_min_lakh": total_property_budget_min,
        "budget_range_max_lakh": total_property_budget_max,
        "text_summary": text_summary,
        "spoken_en": spoken_en,
        "spoken_hi": spoken_hi
    }


def compare_properties(prop_a: Dict[str, Any], prop_b: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes side-by-side comparison of two property listings:
    Price, Area, Price per sqft, Floor, Age/Status, and Location.
    """
    meta_a = prop_a.get("metadata", prop_a)
    meta_b = prop_b.get("metadata", prop_b)

    title_a = meta_a.get("title", "Property A")
    title_b = meta_b.get("title", "Property B")

    price_a = float(meta_a.get("price_lakh") or 0.0)
    price_b = float(meta_b.get("price_lakh") or 0.0)

    area_a = float(meta_a.get("area_sqft") or 0.0)
    area_b = float(meta_b.get("area_sqft") or 0.0)

    rate_a = int(round((price_a * 100000.0) / area_a)) if area_a > 0 else 0
    rate_b = int(round((price_b * 100000.0) / area_b)) if area_b > 0 else 0

    price_diff_lakh = round(abs(price_a - price_b), 2)
    cheaper_title = title_a if price_a < price_b else title_b

    table_md = (
        f"### ⚖️ Property Comparison\n\n"
        f"| Feature | {title_a} | {title_b} |\n"
        f"| :--- | :--- | :--- |\n"
        f"| **Location** | {meta_a.get('location', '')}, {meta_a.get('city', '')} | {meta_b.get('location', '')}, {meta_b.get('city', '')} |\n"
        f"| **Price** | ₹{price_a:g} Lakh | ₹{price_b:g} Lakh |\n"
        f"| **BHK** | {meta_a.get('bhk', '-')} BHK | {meta_b.get('bhk', '-')} BHK |\n"
        f"| **Super Area** | {int(area_a)} sq ft | {int(area_b)} sq ft |\n"
        f"| **Rate / sq ft** | ₹{rate_a:,} / sq ft | ₹{rate_b:,} / sq ft |\n"
        f"| **Status** | {meta_a.get('availability', 'Ready to Move')} | {meta_b.get('availability', 'Ready to Move')} |\n"
    )

    spoken_en = (
        f"Comparing the two: {cheaper_title} is cheaper by {price_diff_lakh} lakh, with a rate of "
        f"₹{min(rate_a, rate_b):,} per square feet. Would you like to schedule visits to both?"
    )

    spoken_hi = (
        f"दोनों विकल्पों की तुलना में {cheaper_title} {price_diff_lakh} लाख रुपये सस्ता है। "
        f"क्या आप दोनों प्रॉपर्टीज की साइट विज़िट प्लान करना चाहेंगे?"
    )

    return {
        "title_a": title_a,
        "title_b": title_b,
        "price_a": price_a,
        "price_b": price_b,
        "area_a": area_a,
        "area_b": area_b,
        "rate_a": rate_a,
        "rate_b": rate_b,
        "price_diff_lakh": price_diff_lakh,
        "table_markdown": table_md,
        "spoken_en": spoken_en,
        "spoken_hi": spoken_hi
    }


def get_site_visit_checklist() -> Dict[str, Any]:
    """
    Returns verified checklist of physical and legal items to verify on a site visit.
    Emphasizes verifying RERA status on the state portal without inventing fake numbers.
    """
    checklist_text = (
        "📋 **Site Visit & Legal Due-Diligence Checklist**:\n\n"
        "**1. Physical Inspection at Site**:\n"
        "• Actual carpet area vs quoted super area (measure room dimensions)\n"
        "• Construction quality, wall finishing, and dampness/seepage signs\n"
        "• Dedicated covered car parking space allotment number\n"
        "• Water source (municipal Ganga water / borewell) & power backup provisions\n\n"
        "**2. Legal Documents to Verify**:\n"
        "• **RERA Registration**: Verify project approval directly on state portal (UP RERA / Delhi RERA)\n"
        "• **Sanctioned Building Plan**: Ensure floor & tower are in approved master plan\n"
        "• **Encumbrance Certificate (EC)**: Confirms property is free of legal mortgages/disputes\n"
        "• **Occupancy / Completion Certificate (OC/CC)** for ready-to-move projects"
    )

    spoken_en = (
        "I have shared your site visit checklist! Be sure to verify carpet area, dedicated parking, "
        "and check the project's official RERA registration on the state portal."
    )

    spoken_hi = (
        "मैंने आपके लिए साइट विज़िट चेकलिस्ट शेयर कर दी है। साइट पर कारपेट एरिया, पार्किंग और "
        "स्टेट रेरा पोर्टल पर प्रोजेक्ट का रजिस्ट्रेशन ज़रूर चेक करें।"
    )

    return {
        "checklist_text": checklist_text,
        "spoken_en": spoken_en,
        "spoken_hi": spoken_hi
    }


def parse_and_calculate_emi(user_text: str, default_principal_lakh: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """
    Detects if user asks an EMI question and parses parameters from text:
    e.g. 'EMI for 60 lakh, 20 years, 8.5%?' or 'What will be the EMI for 75 lakh?'
    """
    lower = user_text.lower()
    has_emi_intent = bool(re.search(r'\b(emi|kist|installment|home loan interest)\b', lower))
    if not has_emi_intent:
        return None

    p_lakh = None
    cr_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:cr|crore)\b', lower)
    if cr_match:
        p_lakh = float(cr_match.group(1)) * 100.0
    else:
        lakh_match = re.search(r'(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:lakh|lac|lacs|l)\b', lower)
        if lakh_match:
            p_lakh = float(lakh_match.group(1))
        else:
            raw_num_match = re.search(r'\b(\d{6,8})\b', lower)
            if raw_num_match:
                p_lakh = float(raw_num_match.group(1)) / 100000.0

    if p_lakh is None:
        p_lakh = default_principal_lakh if default_principal_lakh else 50.0

    y_match = re.search(r'(\d+)\s*(?:year|years|saal|yr|yrs)\b', lower)
    tenure = int(y_match.group(1)) if y_match else 20

    r_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:%|percent|pratishat)', lower)
    rate = float(r_match.group(1)) if r_match else 8.5

    return calculate_emi(principal_lakh=p_lakh, tenure_years=tenure, annual_interest_rate=rate)


def parse_and_estimate_affordability(user_text: str) -> Optional[Dict[str, Any]]:
    """
    Detects affordability queries and extracts salary/income, existing EMIs, and down payment.
    e.g. 'My monthly salary is 1.2 lakh, can I afford a 2BHK flat?'
    """
    lower = user_text.lower()
    has_afford_intent = bool(re.search(r'\b(afford|affordability|salary|income|kamata|aamdani|budget estimate)\b', lower))
    if not has_afford_intent:
        return None

    # Monthly income
    income = 0.0
    # Look for "salary is 1.5 lakh" or "salary 80,000" or "income 1 lakh"
    lakh_income = re.search(r'(?:salary|income|earning|kamata)\s*(?:is|of|hai)?\s*(?:₹|rs\.?)?\s*(\d+(?:\.\d+)?)\s*(?:lakh|lac|lacs|l)\b', lower)
    if lakh_income:
        income = float(lakh_income.group(1)) * 100000.0
    else:
        num_income = re.search(r'(?:salary|income|earning|kamata)\s*(?:is|of|hai)?\s*(?:₹|rs\.?)?\s*(\d{4,7})\b', lower)
        if num_income:
            income = float(num_income.group(1))

    if income <= 0:
        return None

    # Down payment
    down_payment_lakh = 0.0
    dp_match = re.search(r'(?:down\s*payment|savings|cash|bache|jama)\s*(?:is|of|hai)?\s*(?:₹|rs\.?)?\s*(\d+(?:\.\d+)?)\s*(?:lakh|lac|lacs|l)\b', lower)
    if dp_match:
        down_payment_lakh = float(dp_match.group(1))

    # Existing EMIs
    existing_emi = 0.0
    ex_match = re.search(r'(?:existing\s*emi|car\s*loan|personal\s*loan|purani\s*kist)\s*(?:is|of|hai)?\s*(?:₹|rs\.?)?\s*(\d{4,6})\b', lower)
    if ex_match:
        existing_emi = float(ex_match.group(1))

    return estimate_affordability(
        monthly_income=income,
        existing_emis=existing_emi,
        down_payment_lakh=down_payment_lakh
    )
