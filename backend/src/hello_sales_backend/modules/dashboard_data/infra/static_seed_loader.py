"""Static seed loader for dashboard data."""

from __future__ import annotations

from collections.abc import Sequence

from hello_sales_backend.modules.dashboard_data.use_cases.ports import DashboardSeedLoaderPort
from hello_sales_backend.modules.dashboard_data.use_cases.views import DashboardDataEntryView

_SEED_ROWS: tuple[tuple[str, int, str, str, str, str], ...] = (
    (
        "company_overview",
        1,
        "Company Overview",
        'Complete: "We sell ___ to ___ so they can ___."',
        "Text",
        "We sell AI sales agents to B2B companies so they can increase close rates",
        "product_truth_anchor",
    ),
    ("company_overview", 2, "Company Overview", "What industry do you operate in?", "Options", "B2B SaaS", "industry"),
    ("company_overview", 3, "Company Overview", "What is your main pricing model?", "Options", "Subscription", "pricing_model"),
    ("company_overview", 4, "Sales Team", "How many sales reps do you currently have?", "Numeric", "6", "sales_team_size"),
    (
        "company_overview",
        5,
        "Customers",
        "Which customer segment generates most revenue?",
        "Options",
        "SMB",
        "primary_customer_segment",
    ),
    (
        "company_overview",
        6,
        "Sales Process",
        "What is the average customer value? (typical deal size)",
        "Options",
        "$3k-$10k",
        "deal_size_range",
    ),
    (
        "company_overview",
        7,
        "Sales Process",
        "Average sales cycle length (lead -> close)?",
        "Options",
        "30-45 days",
        "avg_sales_cycle",
    ),
    ("company_overview", 8, "Tools", "What CRM do you use?", "Text", "HubSpot", "crm_tool"),
    (
        "company_overview",
        9,
        "Management Signals",
        "What is your biggest sales constraint right now?",
        "Text",
        "Inconsistent messaging",
        "primary_sales_constraint",
    ),
    (
        "company_overview",
        10,
        "Management Signals",
        "What is your main focus this quarter?",
        "Text",
        "Improve close rate",
        "quarterly_sales_focus",
    ),
    (
        "company_overview",
        11,
        "Company Overview",
        "Which product is your current executive priority?",
        "Text",
        "Hello Sales Core",
        "executive_focus_product",
    ),
    ("product_profile", 12, "Product ID", "Internal product code", "Text", "HS-CORE-001", "product_id"),
    ("product_profile", 13, "Product Name", "Product names", "Text", "Hello Sales Core", "product_name"),
    (
        "product_profile",
        14,
        "Product Description",
        "Describe this product in 2-3 sentences",
        "Text",
        "AI sales enablement platform capturing VP sales knowledge",
        "product_description",
    ),
    (
        "product_profile",
        15,
        "Target Customer",
        "Who is this product for?",
        "Options + text",
        "SMB B2B companies",
        "product_target_customer",
    ),
    (
        "product_profile",
        16,
        "Primary Use Case",
        "Main problem this product solves",
        "Text",
        "Improve rep consistency and close rate",
        "product_use_case",
    ),
    (
        "product_profile",
        17,
        "Pricing Model",
        "How is this product priced?",
        "Options",
        "Subscription",
        "product_pricing_model",
    ),
    ("product_profile", 18, "List Price", "Standard list price", "Numeric", "$299 / month", "product_list_price"),
    (
        "product_profile",
        19,
        "Product Sales Cycle",
        "Typical sales cycle for this product",
        "Options",
        "30-45 days",
        "product_sales_cycle",
    ),
    (
        "product_profile",
        20,
        "Deal Size",
        "Typical contract value",
        "Options",
        "$3k-$6k",
        "product_deal_size",
    ),
    ("product_profile", 21, "Revenue Contribution", "% of total revenue", "Numeric", "65%", "product_revenue_share"),
)


class StaticDashboardSeedLoader(DashboardSeedLoaderPort):
    """Load the built-in scaffold dashboard entries without filesystem access."""

    def load_entries(self) -> Sequence[DashboardDataEntryView]:
        return [
            DashboardDataEntryView(
                dataset_key=dataset_key,
                sequence_no=sequence_no,
                section_label=section_label,
                prompt_text=prompt_text,
                answer_type=answer_type,
                example_answer=example_answer,
                entry_id=entry_id,
            )
            for dataset_key, sequence_no, section_label, prompt_text, answer_type, example_answer, entry_id in _SEED_ROWS
        ]
