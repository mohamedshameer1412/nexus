// Makes Nexus installable as an app on phones and desktops.
export default function manifest() {
  return {
    name: "Nexus", short_name: "Nexus", description: "Study from your own materials, with answers you can check.",
    start_url: "/dashboard", scope: "/", display: "standalone", background_color: "#F2F8FC", theme_color: "#0194E2",
    icons: [{ src: "/icon.png", sizes: "256x256", type: "image/png", purpose: "any" }],
  };
}
