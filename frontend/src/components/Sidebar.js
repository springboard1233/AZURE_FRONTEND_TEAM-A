// frontend/src/components/Sidebar.js
import React, { useEffect, useState } from "react";

export default function Sidebar() {
  const [activeSection, setActiveSection] = useState("usage");

  useEffect(() => {
    const sections = document.querySelectorAll("section");
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id);
          }
        });
      },
      { threshold: 0.5 }
    );

    sections.forEach((sec) => observer.observe(sec));
    return () => observer.disconnect();
  }, []);

  const menuStyle = {
    listStyle: "none",
    padding: 0,
    marginTop: 20,
  };

  const linkStyle = (section) => ({
    display: "block",
    padding: "10px 14px",
    cursor: "pointer",
    textDecoration: "none",
    borderRadius: "6px",
    marginBottom: "6px",
    background: activeSection === section ? "#374151" : "transparent", // dark grey for active
    color: activeSection === section ? "#ffffff" : "#d1d5db", // white active, light grey inactive
    fontWeight: activeSection === section ? "bold" : "normal",
    transition: "all 0.3s ease",
  });

  const handleClick = (e, id) => {
    e.preventDefault();
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <aside
      style={{
        width: 220,
        background: "#1f2937", // dark grey sidebar background
        padding: 16,
        position: "sticky",
        top: 0,
        height: "100vh",
        color: "white",
      }}
    >
      <h3 style={{ marginBottom: 20, fontSize: 18, fontWeight: "bold", color: "#f9fafb" }}>
        Azure Dashboard
      </h3>
      <nav>
        <ul style={menuStyle}>
          <li>
            <a
              href="#usage"
              style={linkStyle("usage")}
              onClick={(e) => handleClick(e, "usage")}
            >
              Usage Trends
            </a>
          </li>
          <li>
            <a
              href="#utilization"
              style={linkStyle("utilization")}
              onClick={(e) => handleClick(e, "utilization")}
            >
              CPU Utilization
            </a>
          </li>
          <li>
            <a
              href="#efficiency"
              style={linkStyle("efficiency")}
              onClick={(e) => handleClick(e, "efficiency")}
            >
              Storage Efficiency
            </a>
          </li>
          <li>
            <a
              href="#forecast"
              style={linkStyle("forecast")}
              onClick={(e) => handleClick(e, "forecast")}
            >
              Forecasts
            </a>
          </li>
          
        </ul>
      </nav>
    </aside>
  );
}
