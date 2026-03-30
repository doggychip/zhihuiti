import { randomUUID } from "crypto";
import { eq } from "drizzle-orm";
import { db } from "../db";
import { products } from "@shared/schema";
import type { Product, InsertProduct } from "@shared/schema";

export async function getAllProducts(): Promise<Product[]> {
  return db.select().from(products).orderBy(products.createdAt);
}

export async function getProduct(id: string): Promise<Product | undefined> {
  const rows = await db.select().from(products).where(eq(products.id, id));
  return rows[0];
}

export async function createProduct(data: InsertProduct): Promise<Product> {
  const id = randomUUID();
  const [product] = await db
    .insert(products)
    .values({ ...data, id, createdAt: new Date() })
    .returning();
  return product;
}

export async function updateProduct(
  id: string,
  data: Partial<Product>,
): Promise<Product | undefined> {
  const [updated] = await db
    .update(products)
    .set(data)
    .where(eq(products.id, id))
    .returning();
  return updated;
}
