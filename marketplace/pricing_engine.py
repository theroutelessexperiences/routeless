from datetime import date
from django.db.models import F
from decimal import Decimal
from marketplace.models import Experience, DynamicPricingRule, DemandSignal

def calculate_dynamic_price(experience, target_date=None):
    """
    Computes the final price for an experience on a given date by applying
    all active DynamicPricingRules. Also considers DemandSignals.
    """
    if target_date is None:
        target_date = date.today()

    base_price = experience.price_per_person
    final_price = base_price

    # 1. Apply rules (eg. Weekend surge, Holiday pricing)
    active_rules = DynamicPricingRule.objects.filter(
        experience=experience,
        active=True
    ).exclude(
        start_date__isnull=False, start_date__gt=target_date
    ).exclude(
        end_date__isnull=False, end_date__lt=target_date
    )

    combined_multiplier = Decimal('1.00')
    
    # Check if target date is a weekend (0=Mon, 6=Sun)
    is_weekend = target_date.weekday() >= 5
    
    for rule in active_rules:
        if rule.rule_type == 'WEEKEND' and not is_weekend:
            continue
        combined_multiplier *= rule.multiplier

    # 2. Demand Surge (compute dynamically)
    # If 10+ people have booked or searched for this date, trigger surge
    demand_signal = DemandSignal.objects.filter(experience=experience, date=target_date).first()
    if demand_signal:
        total_interest = demand_signal.search_count + (demand_signal.booking_attempts * 3)
        if total_interest > 50:
             combined_multiplier *= Decimal('1.25') # 25% High demand surge
        elif total_interest > 20:
             combined_multiplier *= Decimal('1.10') # 10% Medium demand surge

    # Cap max multiplier at 3x to prevent absurd pricing
    if combined_multiplier > Decimal('3.00'):
        combined_multiplier = Decimal('3.00')

    final_price = base_price * combined_multiplier
    
    # Return rounded to nearest whole rupee
    return int(final_price.quantize(Decimal('1')))
