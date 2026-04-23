from __future__ import annotations


async def test_company_profile_and_products_api_has_no_seeded_data(client) -> None:
    empty_profile = await client.get("/api/company-profile")
    empty_products = await client.get("/api/products")

    assert empty_profile.status_code == 200
    assert empty_profile.json()["data"] is None
    assert empty_products.status_code == 200
    assert empty_products.json()["data"] == []

    profile_response = await client.put(
        "/api/company-profile",
        json={
            "company_name": "HelloSales",
            "industry": "B2B SaaS",
            "target_customer": "SMB sales teams",
            "pricing_model": "Subscription",
            "sales_team_size": 6,
            "crm_tool": "HubSpot",
            "average_deal_size": "$3k-$10k",
            "average_sales_cycle": "30-45 days",
            "primary_sales_constraint": "Inconsistent messaging",
            "quarterly_sales_focus": "Improve close rate",
        },
    )
    assert profile_response.status_code == 200
    profile = profile_response.json()["data"]
    assert profile["company_name"] == "HelloSales"

    product_response = await client.post(
        "/api/products",
        json={
            "product_name": "Hello Sales Core",
            "product_description": "AI sales enablement platform",
            "target_customer": "SMB B2B companies",
            "primary_use_case": "Improve rep consistency",
            "pricing_model": "Subscription",
            "list_price": "$299 / month",
            "sales_cycle": "30-45 days",
            "deal_size": "$3k-$6k",
            "revenue_share": "65%",
            "is_primary": True,
        },
    )
    assert product_response.status_code == 200
    product = product_response.json()["data"]
    assert product["company_profile_id"] == profile["profile_id"]
    assert product["product_name"] == "Hello Sales Core"

    context_response = await client.get("/api/company-context")
    assert context_response.status_code == 200
    context = context_response.json()["data"]
    assert context["company_profile"]["company_name"] == "HelloSales"
    assert context["products"][0]["product_name"] == "Hello Sales Core"
