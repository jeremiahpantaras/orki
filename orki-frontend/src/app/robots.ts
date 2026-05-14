import { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/dashboard/", "/(main)/", "/api/"],
    },
    sitemap: "https://orki.cosedevs.com/sitemap.xml",
  };
}
