import { Stagehand } from "@browserbasehq/stagehand";

const PRODUCT_ID = "neiqwz";
const GUMROAD_EDIT = `https://gumroad.com/products/${PRODUCT_ID}/edit`;
const GUMROAD_PUBLIC = `https://newbiezz.gumroad.com/l/${PRODUCT_ID}`;
const FREE_TOOL = "https://leverage-tools.pages.dev/fabrication-quote-calculator/?utm_source=gumroad&utm_medium=product&utm_campaign=p001&utm_content=free-calculator";

const instruction = `Open ${GUMROAD_EDIT}. Update only the product description for Product ${PRODUCT_ID} so it contains a clearly clickable link labeled "Try the FREE Fabrication Quote Calculator" pointing exactly to ${FREE_TOOL}. Preserve the product name and price. Do not change payout settings, payment credentials, account settings, or any financial settings. Save the change. Then open ${GUMROAD_PUBLIC} and verify the label and exact link are visible and clickable. Return structured JSON with success, verification, and a concise action summary.`;

if (!process.env.BROWSERBASE_API_KEY) {
  throw new Error("BROWSERBASE_API_KEY is not configured");
}

const contextId = process.env.BROWSERBASE_GUMROAD_CONTEXT_ID;
const sessionConfig = contextId
  ? { browserSettings: { context: { id: contextId, persist: true } } }
  : undefined;

const stagehand = new Stagehand({
  env: "BROWSERBASE",
  apiKey: process.env.BROWSERBASE_API_KEY,
  model: process.env.BROWSERBASE_MODEL || "openai/gpt-5",
  browserbaseSessionCreateParams: sessionConfig,
  disablePino: true,
});

await stagehand.init();

try {
  const page = stagehand.context.pages()[0] || await stagehand.context.newPage();
  await page.goto(GUMROAD_EDIT, { waitUntil: "domcontentloaded" });

  const agent = stagehand.agent({
    systemPrompt: [
      "You are Leverage's guarded Gumroad web automation worker.",
      "Only modify the specified Product description and save it.",
      "Never change price, payout, bank, payment, account, password, email, or other financial/security settings.",
      "Verify the final public product page after saving.",
      "Do not publish, unpublish, delete, refund, or perform any financial action.",
      "Return structured JSON only when possible."
    ].join(" "),
  });

  const result = await agent.execute({ instruction, maxSteps: 12 });
  console.log(JSON.stringify({
    ok: true,
    product_id: PRODUCT_ID,
    route: "browserbase_stagehand",
    session_id: stagehand.browserbaseSessionID,
    result,
    target_url: FREE_TOOL,
  }, null, 2));
} finally {
  await stagehand.close();
}
