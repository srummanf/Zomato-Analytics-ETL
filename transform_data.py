"""Step 5: Data Transformation — PySpark job on top of the validated
(valid_*.csv) files from validate_data.py.

Cleans/casts types, explodes `cuisines` into a restaurant<->cuisine bridge
table, takes the primary `rest_type` as restaurant_type, parses `reviews_list`
into real fact_reviews rows, and derives metrics (order_hour,
customer_order_count).

Runs inside Docker (see Dockerfile) so PySpark gets a JVM it actually supports,
regardless of the host machine's Java version. Output is written with pandas
(not Spark's native CSV writer) to keep one flat file per table, matching the
rest of the pipeline's raw_/valid_/clean_ convention, and to sidestep Spark's
Hadoop-committer machinery entirely.
"""
import ast
import re
from pathlib import Path

from pyspark.sql import SparkSession, functions as F, types as T

DATA_DIR = Path(__file__).parent / "data"

RESTAURANT_SCHEMA = T.StructType([
    T.StructField("url", T.StringType()),
    T.StructField("address", T.StringType()),
    T.StructField("name", T.StringType()),
    T.StructField("online_order", T.StringType()),
    T.StructField("book_table", T.StringType()),
    T.StructField("rate", T.StringType()),
    T.StructField("votes", T.StringType()),
    T.StructField("phone", T.StringType()),
    T.StructField("location", T.StringType()),
    T.StructField("rest_type", T.StringType()),
    T.StructField("dish_liked", T.StringType()),
    T.StructField("cuisines", T.StringType()),
    T.StructField("approx_cost(for two people)", T.StringType()),
    T.StructField("reviews_list", T.StringType()),
    T.StructField("menu_item", T.StringType()),
    T.StructField("listed_in(type)", T.StringType()),
    T.StructField("listed_in(city)", T.StringType()),
    T.StructField("restaurant_id", T.StringType()),
])

CUSTOMER_SCHEMA = T.StructType([
    T.StructField("customer_id", T.StringType()),
    T.StructField("name", T.StringType()),
    T.StructField("email", T.StringType()),
    T.StructField("phone", T.StringType()),
    T.StructField("signup_date", T.StringType()),
])

ORDER_SCHEMA = T.StructType([
    T.StructField("order_id", T.StringType()),
    T.StructField("customer_id", T.StringType()),
    T.StructField("restaurant_id", T.StringType()),
    T.StructField("order_date", T.StringType()),
    T.StructField("order_time", T.StringType()),
    T.StructField("party_size", T.StringType()),
    T.StructField("order_total", T.StringType()),
    T.StructField("order_status", T.StringType()),
])

ORDER_ITEM_SCHEMA = T.StructType([
    T.StructField("order_item_id", T.StringType()),
    T.StructField("order_id", T.StringType()),
    T.StructField("item_name", T.StringType()),
    T.StructField("item_price", T.StringType()),
])

PAYMENT_SCHEMA = T.StructType([
    T.StructField("payment_id", T.StringType()),
    T.StructField("order_id", T.StringType()),
    T.StructField("payment_method", T.StringType()),
    T.StructField("amount", T.StringType()),
    T.StructField("payment_status", T.StringType()),
])

DELIVERY_SCHEMA = T.StructType([
    T.StructField("delivery_id", T.StringType()),
    T.StructField("order_id", T.StringType()),
    T.StructField("delivery_partner_id", T.StringType()),
    T.StructField("delivery_partner_name", T.StringType()),
    T.StructField("delivery_time_minutes", T.StringType()),
    T.StructField("delivery_status", T.StringType()),
])

REVIEW_ARRAY_SCHEMA = T.ArrayType(T.StructType([
    T.StructField("review_rating", T.DoubleType()),
    T.StructField("review_text", T.StringType()),
]))


def get_spark():
    return (
        SparkSession.builder
        .appName("zomato-transform")
        .master("local[*]")
        .config("spark.driver.memory", "2g")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )


def read_csv(spark, name, schema):
    return (
        spark.read
        .option("header", True)
        .option("multiLine", True)
        .option("escape", '"')
        .schema(schema)
        .csv(str(DATA_DIR / f"valid_{name}.csv"))
    )


def parse_reviews(reviews_str):
    if not reviews_str:
        return []
    try:
        tuples = ast.literal_eval(reviews_str)
    except (ValueError, SyntaxError):
        return None
    parsed = []
    for rating_str, text in tuples:
        match = re.search(r"(\d+(\.\d+)?)", rating_str or "")
        rating = float(match.group(1)) if match else None
        clean_text = (text or "").replace("RATED", "", 1).strip()
        parsed.append({"review_rating": rating, "review_text": clean_text})
    return parsed


def build_fact_reviews(restaurants):
    parse_reviews_udf = F.udf(parse_reviews, REVIEW_ARRAY_SCHEMA)
    with_parsed = restaurants.select(
        "restaurant_id", parse_reviews_udf(F.col("reviews_list")).alias("parsed_reviews")
    )

    failed = with_parsed.filter(F.col("parsed_reviews").isNull())
    failed_pdf = failed.select("restaurant_id").toPandas()
    if not failed_pdf.empty:
        failed_pdf["reject_reason"] = "unparseable_reviews_list"
        failed_pdf.to_csv(DATA_DIR / "rejected_reviews.csv", index=False)
        print(f"WARNING: {len(failed_pdf)} restaurants had unparseable reviews_list "
              f"-> data/rejected_reviews.csv")

    fact_reviews = (
        with_parsed
        .filter(F.col("parsed_reviews").isNotNull())
        .select("restaurant_id", F.explode("parsed_reviews").alias("review"))
        .select(
            "restaurant_id",
            F.col("review.review_rating").alias("review_rating"),
            F.col("review.review_text").alias("review_text"),
        )
    )
    return fact_reviews


def build_clean_restaurants(restaurants):
    return (
        restaurants
        .withColumn("restaurant_name", F.trim(F.col("name")))
        .withColumn("area", F.col("location"))
        .withColumn("restaurant_type", F.trim(F.split(F.col("rest_type"), ",")[0]))
        .withColumn("meal_type", F.col("`listed_in(type)`"))
        .withColumn("rating", F.regexp_extract(F.col("rate"), r"(\d\.\d)", 1).cast("double"))
        .withColumn("vote_count", F.col("votes").cast("int"))
        .withColumn("online_order_enabled", F.col("online_order") == F.lit("Yes"))
        .withColumn("table_booking_enabled", F.col("book_table") == F.lit("Yes"))
        .withColumn(
            "avg_cost_for_two",
            F.regexp_replace(F.col("`approx_cost(for two people)`"), ",", "").cast("double"),
        )
        .select(
            "restaurant_id", "restaurant_name", "url", "address", "area",
            "restaurant_type", "meal_type", "rating", "vote_count",
            "avg_cost_for_two", "online_order_enabled", "table_booking_enabled",
        )
    )


def build_restaurant_cuisines(restaurants):
    return (
        restaurants
        .select(
            "restaurant_id",
            F.explode(F.split(F.coalesce(F.col("cuisines"), F.lit("")), r",\s*")).alias("cuisine"),
        )
        .withColumn("cuisine", F.trim(F.col("cuisine")))
        .filter(F.col("cuisine") != "")
    )


def build_clean_customers(customers, orders):
    order_counts = orders.groupBy("customer_id").agg(F.count("*").alias("customer_order_count"))
    return (
        customers
        .join(order_counts, "customer_id", "left")
        .fillna({"customer_order_count": 0})
    )


def build_clean_orders(orders):
    return (
        orders
        .withColumn("order_date", F.to_date("order_date"))
        .withColumn("order_hour", F.split(F.col("order_time"), ":")[0].cast("int"))
        .withColumn("party_size", F.col("party_size").cast("int"))
        .withColumn("order_total", F.col("order_total").cast("double"))
    )


def write_csv(df, name):
    pdf = df.toPandas()
    path = DATA_DIR / f"clean_{name}.csv"
    pdf.to_csv(path, index=False)
    print(f"Wrote {path} ({len(pdf)} rows)")


def main():
    spark = get_spark()
    try:
        restaurants = read_csv(spark, "restaurants", RESTAURANT_SCHEMA)
        customers = read_csv(spark, "customers", CUSTOMER_SCHEMA)
        orders = read_csv(spark, "orders", ORDER_SCHEMA)
        order_items = read_csv(spark, "order_items", ORDER_ITEM_SCHEMA)
        payments = read_csv(spark, "payments", PAYMENT_SCHEMA)
        deliveries = read_csv(spark, "deliveries", DELIVERY_SCHEMA)

        write_csv(build_clean_restaurants(restaurants), "restaurants")
        write_csv(build_restaurant_cuisines(restaurants), "restaurant_cuisines")
        write_csv(build_fact_reviews(restaurants), "reviews")
        write_csv(build_clean_customers(customers, orders), "customers")
        write_csv(build_clean_orders(orders), "orders")
        write_csv(order_items.withColumn("item_price", F.col("item_price").cast("double")), "order_items")
        write_csv(payments.withColumn("amount", F.col("amount").cast("double")), "payments")
        write_csv(
            deliveries.withColumn(
                "delivery_time_minutes", F.col("delivery_time_minutes").cast("int")
            ),
            "deliveries",
        )
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
