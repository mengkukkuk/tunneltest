/**
 * Cloudflare Worker — proxy ระหว่าง GitHub Pages กับ Backend (ผ่าน Cloudflare Tunnel)
 *
 * ทำไมต้องมี Worker:
 * - GitHub Pages เป็น static site, เรียก local backend ตรงๆ ผ่าน HTTPS
 *   จะมีปัญหา CORS หรือ mixed-content ถ้า config tunnel domain ไม่ตรง origin
 * - ใส่ TUNNEL_URL ไว้ฝั่ง server (Worker) ปลอดภัยกว่าใส่ใน frontend
 *
 * วิธี deploy: ดู README.md ในโฟลเดอร์ worker/
 */

const TUNNEL_URL = "https://make-ohio-controversy-pressure.trycloudflare.com";
// หรือถ้าตั้ง named tunnel ไว้กับ domain ตัวเอง:
// const TUNNEL_URL = "https://scada-api.yourdomain.com";

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: corsHeaders(),
      });
    }

    // ใช้ env var ถ้ามี (ตั้งผ่าน wrangler secret/vars) ไม่งั้น fallback เป็นค่า hardcode ด้านบน
    const target = (env && env.TUNNEL_URL) || TUNNEL_URL;
    const forwardUrl = target + url.pathname + url.search;

    try {
      const resp = await fetch(forwardUrl, {
        method: request.method,
        headers: request.headers,
        body: ["GET", "HEAD"].includes(request.method) ? undefined : await request.text(),
      });

      const body = await resp.text();
      return new Response(body, {
        status: resp.status,
        headers: {
          "Content-Type": resp.headers.get("Content-Type") || "application/json",
          ...corsHeaders(),
        },
      });
    } catch (err) {
      return new Response(
        JSON.stringify({ status: "error", message: `Worker could not reach tunnel: ${err.message}` }),
        { status: 502, headers: { "Content-Type": "application/json", ...corsHeaders() } }
      );
    }
  },
};

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*", // ทดสอบก่อน — ทีหลังเปลี่ยนเป็น GitHub Pages domain จริง
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}
