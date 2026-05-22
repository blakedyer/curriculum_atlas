document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-contact-toggle]").forEach((shell) => {
    const button = shell.querySelector(".contact-compact__button");
    const panel = shell.querySelector(".contact-compact__panel");

    if (!button || !panel) {
      return;
    }

    const applyExpanded = (expanded) => {
      shell.classList.toggle("is-open", expanded);
      button.setAttribute("aria-expanded", String(expanded));
      panel.hidden = !expanded;
    };

    button.addEventListener("click", () => {
      const expanded = button.getAttribute("aria-expanded") === "true";
      applyExpanded(!expanded);
    });

    applyExpanded(false);
  });

  document.querySelectorAll("[data-card-filter]").forEach((panel) => {
    const grid = panel.parentElement?.querySelector("[data-filter-grid]");
    const emptyState = panel.parentElement?.querySelector("[data-filter-empty]");
    const buttons = Array.from(panel.querySelectorAll("[data-filter-group]"));
    const searchInput = panel.querySelector("[data-filter-search-input]");
    const countLabel = panel.querySelector("[data-filter-count]");
    const clearButton = panel.querySelector("[data-filter-clear]");

    if (!grid) {
      return;
    }

    const cards = Array.from(grid.children);
    const countNoun = (countLabel?.textContent || "items").replace(/^\d+\s*/, "") || "items";

    const activeFilters = {};
    buttons.forEach((button) => {
      const group = button.getAttribute("data-filter-group");
      if (!group || activeFilters[group]) {
        return;
      }
      const activeButton =
        buttons.find(
          (candidate) =>
            candidate.getAttribute("data-filter-group") === group &&
            candidate.classList.contains("is-active"),
        ) ||
        buttons.find((candidate) => candidate.getAttribute("data-filter-group") === group);
      if (activeButton) {
        activeFilters[group] = activeButton.getAttribute("data-filter-value") || "all";
      }
    });

    const applyFilters = () => {
      const query = (searchInput?.value || "").trim().toLowerCase();
      let visibleCount = 0;

      cards.forEach((card) => {
        const matchesSearch = !query || (card.getAttribute("data-filter-search") || "").includes(query);
        const matchesGroups = Object.entries(activeFilters).every(([group, value]) => {
          if (!value || value === "all") {
            return true;
          }
          const haystack = card.getAttribute(`data-filter-${group}`) || "";
          return haystack.split(/\s+/).includes(value);
        });
        const isVisible = matchesSearch && matchesGroups;
        card.classList.toggle("is-hidden", !isVisible);
        if (isVisible) {
          visibleCount += 1;
        }
      });

      if (emptyState) {
        emptyState.classList.toggle("is-hidden", visibleCount !== 0);
      }
      if (countLabel) {
        countLabel.textContent = `${visibleCount} ${countNoun}`;
      }
    };

    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        const group = button.getAttribute("data-filter-group");
        const value = button.getAttribute("data-filter-value") || "all";
        if (!group) {
          return;
        }
        activeFilters[group] = value;
        buttons.forEach((candidate) => {
          if (candidate.getAttribute("data-filter-group") !== group) {
            return;
          }
          const isActive = candidate === button;
          candidate.classList.toggle("is-active", isActive);
          candidate.setAttribute("aria-pressed", String(isActive));
        });
        applyFilters();
      });
    });

    if (searchInput) {
      searchInput.addEventListener("input", applyFilters);
    }

    if (clearButton) {
      clearButton.addEventListener("click", () => {
        if (searchInput) {
          searchInput.value = "";
        }
        Object.keys(activeFilters).forEach((group) => {
          activeFilters[group] = "all";
          buttons.forEach((button) => {
            if (button.getAttribute("data-filter-group") !== group) {
              return;
            }
            const isActive = (button.getAttribute("data-filter-value") || "all") === "all";
            button.classList.toggle("is-active", isActive);
            button.setAttribute("aria-pressed", String(isActive));
          });
        });
        applyFilters();
      });
    }

    applyFilters();
  });

  document.querySelectorAll("[data-graph-switcher]").forEach((shell) => {
    const graphStage = shell.querySelector("[data-graph-stage]");
    const graphLink = shell.querySelector("[data-graph-link]");
    const modeCopy = shell.querySelector("[data-graph-mode-copy]");
    const graphSearchInput = shell.querySelector("[data-graph-search-input]");
    const graphSearchDockBody = graphSearchInput?.closest(".graph-search-dock__body");
    const graphSearchStatus = shell.querySelector("[data-graph-search-status]");
    const resetButton = shell.querySelector("[data-graph-reset]");
    const buttons = Array.from(shell.querySelectorAll("[data-graph-mode]"));
    const templates = Array.from(shell.querySelectorAll("[data-graph-template]"));
    const analyticsShell = shell.querySelector("[data-graph-analytics]");
    const analyticsDataScript = analyticsShell?.querySelector("[data-graph-analytics-data]");
    const analyticsButtons = Array.from(analyticsShell?.querySelectorAll("[data-analytics-mode]") || []);
    const analyticsSelect = analyticsShell?.querySelector("[data-analytics-mode-select]");
    const analyticsSummary = analyticsShell?.querySelector("[data-analytics-summary]");
    const overlayLegend = shell.querySelector("[data-graph-overlay-legend]");
    const overlayLegendBody = overlayLegend?.querySelector("[data-graph-overlay-legend-body]") || overlayLegend;
    const overlayLegendSummary = overlayLegend?.querySelector("[data-graph-overlay-legend-summary]");
    const baseLegendDataScript = shell.querySelector("[data-graph-overlay-legend-data]");

    if (!graphStage || buttons.length === 0) {
      return;
    }

    const analyticsLayerPalette = {
      bottleneck: [
        { label: "Low", detail: "Smaller SEOS downstream reach", color: "oklch(93% 0.045 86)" },
        { label: "Moderate", detail: "Growing SEOS dependency reach", color: "oklch(85% 0.08 78)" },
        { label: "High", detail: "Large SEOS dependency reach", color: "oklch(73% 0.13 64)" },
        { label: "Very high", detail: "Highest SEOS blocking factor", color: "oklch(60% 0.16 48)" },
      ],
      delay: [
        { label: "Start", detail: "No or few prerequisite steps before this course", color: "oklch(93% 0.035 245)" },
        { label: "Building", detail: "Some prerequisite sequence before this course", color: "oklch(82% 0.07 255)" },
        { label: "Deep", detail: "Long prerequisite sequence before this course", color: "oklch(70% 0.11 270)" },
        { label: "Deepest", detail: "Largest prerequisite chain depth in this graph", color: "oklch(58% 0.15 286)" },
      ],
      cleanup: [
        { label: "Course with cleanup flag", detail: "Direct prerequisite list can be simplified", color: "oklch(87% 0.11 82)" },
      ],
      year: [
        { token: "year-1", label: "Year 1", detail: "Courses placed in the first program year", color: "oklch(84% 0.1 190)" },
        { token: "year-2", label: "Year 2", detail: "Courses placed in the second program year", color: "oklch(86% 0.13 92)" },
        { token: "years-3-4", label: "Years 3 + 4", detail: "Courses placed in the upper-year program band", color: "oklch(79% 0.15 28)" },
      ],
    };

    const graphViewState = new WeakMap();
    const getActiveSvg = () => graphStage.querySelector("svg");
    const autocompletePanel = document.createElement("div");
    let graphAutocompleteOptions = [];
    let activeAutocompleteIndex = -1;
    let activeAnalyticsMode = "base";
    let analyticsData = null;
    let baseLegendData = null;

    if (analyticsDataScript?.textContent) {
      try {
        analyticsData = JSON.parse(analyticsDataScript.textContent);
      } catch {
        analyticsData = null;
      }
    }

    if (baseLegendDataScript?.textContent) {
      try {
        baseLegendData = JSON.parse(baseLegendDataScript.textContent);
      } catch {
        baseLegendData = null;
      }
    }

    if (graphSearchInput) {
      autocompletePanel.id = `${shell.id || "graph"}-course-autocomplete`;
      autocompletePanel.className = "graph-search-autocomplete";
      autocompletePanel.setAttribute("role", "listbox");
      autocompletePanel.hidden = true;
      graphSearchInput.setAttribute("aria-autocomplete", "list");
      graphSearchInput.setAttribute("aria-controls", autocompletePanel.id);
      graphSearchInput.closest(".graph-search")?.insertAdjacentElement("afterend", autocompletePanel);
    }

    const parseViewBox = (svg) => {
      const attr = svg?.getAttribute("viewBox");
      if (!attr) {
        return null;
      }
      const parts = attr
        .trim()
        .split(/\s+/)
        .map((part) => Number(part));
      if (parts.length !== 4 || !parts.every(Number.isFinite)) {
        return null;
      }
      return {
        x: parts[0],
        y: parts[1],
        width: parts[2],
        height: parts[3],
      };
    };

    const getDefaultViewBox = (svg) => {
      if (!svg) {
        return null;
      }
      if (graphViewState.has(svg)) {
        return graphViewState.get(svg);
      }

      let viewBox = parseViewBox(svg);
      if (!viewBox && svg.viewBox?.baseVal) {
        const base = svg.viewBox.baseVal;
        viewBox = {
          x: base.x,
          y: base.y,
          width: base.width,
          height: base.height,
        };
      }

      if (viewBox) {
        graphViewState.set(svg, viewBox);
      }
      return viewBox;
    };

    const getCurrentViewBox = (svg) => parseViewBox(svg) || getDefaultViewBox(svg);
    const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

    const constrainViewBox = (svg, viewBox) => {
      const defaultViewBox = getDefaultViewBox(svg);
      if (!defaultViewBox) {
        return viewBox;
      }

      const width = clamp(viewBox.width, defaultViewBox.width * 0.16, defaultViewBox.width);
      const height = clamp(viewBox.height, defaultViewBox.height * 0.16, defaultViewBox.height);
      const maxX = defaultViewBox.x + defaultViewBox.width - width;
      const maxY = defaultViewBox.y + defaultViewBox.height - height;
      return {
        x: clamp(viewBox.x, defaultViewBox.x, Math.max(defaultViewBox.x, maxX)),
        y: clamp(viewBox.y, defaultViewBox.y, Math.max(defaultViewBox.y, maxY)),
        width,
        height,
      };
    };

    const setViewBox = (svg, viewBox) => {
      const nextViewBox = constrainViewBox(svg, viewBox);
      svg.setAttribute(
        "viewBox",
        `${nextViewBox.x.toFixed(2)} ${nextViewBox.y.toFixed(2)} ${nextViewBox.width.toFixed(2)} ${nextViewBox.height.toFixed(2)}`,
      );
    };

    const centerScrollableGraphFrame = (svg) => {
      if (!document.body.classList.contains("page--secret-computing")) {
        return;
      }
      const frame = svg?.closest(".graph-frame");
      if (!frame) {
        return;
      }
      window.requestAnimationFrame(() => {
        frame.scrollTo({
          left: Math.max(0, (svg.scrollWidth - frame.clientWidth) / 2),
          top: Math.max(0, (svg.scrollHeight - frame.clientHeight) / 2),
          behavior: "smooth",
        });
      });
    };

    const restoreScrollableGraphFrame = (svg) => {
      if (!document.body.classList.contains("page--secret-computing")) {
        return;
      }
      const frame = svg?.closest(".graph-frame");
      if (frame) {
        frame.scrollTo({ left: 0, top: 0, behavior: "smooth" });
      }
    };

    const clientPointToSvgPoint = (svg, clientX, clientY) => {
      const matrix = svg.getScreenCTM();
      if (!matrix) {
        const current = getCurrentViewBox(svg);
        return current
          ? {
              x: current.x + current.width / 2,
              y: current.y + current.height / 2,
            }
          : null;
      }
      const point = svg.createSVGPoint();
      point.x = clientX;
      point.y = clientY;
      return point.matrixTransform(matrix.inverse());
    };

    const zoomGraph = (svg, factor, clientX, clientY) => {
      const current = getCurrentViewBox(svg);
      const focusPoint = clientPointToSvgPoint(svg, clientX, clientY);
      if (!current || !focusPoint) {
        return;
      }

      const width = current.width * factor;
      const height = current.height * factor;
      const focusXRatio = (focusPoint.x - current.x) / current.width;
      const focusYRatio = (focusPoint.y - current.y) / current.height;
      setViewBox(svg, {
        x: focusPoint.x - width * focusXRatio,
        y: focusPoint.y - height * focusYRatio,
        width,
        height,
      });
    };

    const getElementBounds = (svg, element) => {
      let bbox;
      let matrix;
      try {
        bbox = element.getBBox();
        const rootMatrix = svg.getScreenCTM();
        const elementMatrix = element.getScreenCTM();
        matrix = rootMatrix && elementMatrix ? rootMatrix.inverse().multiply(elementMatrix) : null;
      } catch {
        return null;
      }
      if (!bbox || !matrix) {
        return null;
      }

      const point = svg.createSVGPoint();
      const transformPoint = (x, y) => {
        point.x = x;
        point.y = y;
        return point.matrixTransform(matrix);
      };
      const corners = [
        transformPoint(bbox.x, bbox.y),
        transformPoint(bbox.x + bbox.width, bbox.y),
        transformPoint(bbox.x, bbox.y + bbox.height),
        transformPoint(bbox.x + bbox.width, bbox.y + bbox.height),
      ];
      return {
        minX: Math.min(...corners.map((corner) => corner.x)),
        maxX: Math.max(...corners.map((corner) => corner.x)),
        minY: Math.min(...corners.map((corner) => corner.y)),
        maxY: Math.max(...corners.map((corner) => corner.y)),
      };
    };

    const focusGraphElements = (svg, elements) => {
      const defaultViewBox = getDefaultViewBox(svg);
      if (!defaultViewBox) {
        return;
      }

      const bounds = elements.map((element) => getElementBounds(svg, element)).filter(Boolean);
      if (bounds.length === 0) {
        return;
      }

      const minX = Math.min(...bounds.map((bound) => bound.minX));
      const maxX = Math.max(...bounds.map((bound) => bound.maxX));
      const minY = Math.min(...bounds.map((bound) => bound.minY));
      const maxY = Math.max(...bounds.map((bound) => bound.maxY));
      const nodeWidth = Math.max(maxX - minX, 1);
      const nodeHeight = Math.max(maxY - minY, 1);
      const centerX = minX + nodeWidth / 2;
      const centerY = minY + nodeHeight / 2;
      const aspect = defaultViewBox.width / defaultViewBox.height;
      const padding = Math.max(32, Math.max(nodeWidth, nodeHeight) * 0.14);
      let width = Math.max(nodeWidth + padding * 2, defaultViewBox.width * 0.24, 140);
      let height = width / aspect;
      if (height < nodeHeight + padding * 2) {
        height = nodeHeight + padding * 2;
        width = height * aspect;
      }

      width = Math.min(width, defaultViewBox.width);
      height = Math.min(height, defaultViewBox.height);
      const maxXOffset = defaultViewBox.x + defaultViewBox.width - width;
      const maxYOffset = defaultViewBox.y + defaultViewBox.height - height;
      setViewBox(svg, {
        x: clamp(centerX - width / 2, defaultViewBox.x, maxXOffset),
        y: clamp(centerY - height / 2, defaultViewBox.y, maxYOffset),
        width,
        height,
      });
      centerScrollableGraphFrame(svg);
    };

    const restoreGraphView = (svg = getActiveSvg()) => {
      const defaultViewBox = getDefaultViewBox(svg);
      if (defaultViewBox) {
        setViewBox(svg, defaultViewBox);
        restoreScrollableGraphFrame(svg);
      }
    };

    const injectGraphSearchStyles = (svg) => {
      if (!svg || svg.querySelector("#atlas-graph-search-style")) {
        return;
      }
      const style = document.createElementNS("http://www.w3.org/2000/svg", "style");
      style.id = "atlas-graph-search-style";
      style.textContent = `
        svg.atlas-searching g.node:not(.is-atlas-context),
        svg.atlas-searching g.edge:not(.is-atlas-branch) {
          opacity: 0.12;
          transition: opacity 160ms ease-out;
        }
        g.edge.is-atlas-branch path {
          stroke: #0f4154 !important;
          stroke-width: 3px !important;
        }
        g.edge.is-atlas-branch polygon {
          fill: #0f4154 !important;
          stroke: #0f4154 !important;
          stroke-width: 1.4px !important;
        }
        g.node.is-atlas-context:not(.is-atlas-match) polygon,
        g.node.is-atlas-context:not(.is-atlas-match) ellipse,
        g.node.is-atlas-context:not(.is-atlas-match) path {
          stroke: #0f4154 !important;
          stroke-width: 2.4px !important;
        }
        g.node.is-atlas-match {
          filter: drop-shadow(0 0 8px rgba(31, 79, 102, 0.42));
        }
        g.node.is-atlas-match polygon,
        g.node.is-atlas-match ellipse,
        g.node.is-atlas-match path {
          fill: #fff1cf !important;
          stroke: #0f4154 !important;
          stroke-width: 4px !important;
        }
        g.node.is-atlas-match text {
          fill: #0f2630 !important;
          font-weight: 700;
        }
        svg.atlas-analytics-active g.node.analytics-muted {
          opacity: 0.34;
        }
        svg.is-analytics-bottleneck g.node.is-analytics-level-1 path,
        svg.is-analytics-bottleneck g.node.is-analytics-level-1 polygon,
        svg.is-analytics-bottleneck g.node.is-analytics-level-1 ellipse {
          fill: oklch(93% 0.045 86) !important;
          stroke: oklch(51% 0.09 58) !important;
          stroke-width: 1.8px !important;
        }
        svg.is-analytics-bottleneck g.node.is-analytics-level-2 path,
        svg.is-analytics-bottleneck g.node.is-analytics-level-2 polygon,
        svg.is-analytics-bottleneck g.node.is-analytics-level-2 ellipse {
          fill: oklch(85% 0.08 78) !important;
          stroke: oklch(45% 0.12 54) !important;
          stroke-width: 2.2px !important;
        }
        svg.is-analytics-bottleneck g.node.is-analytics-level-3 path,
        svg.is-analytics-bottleneck g.node.is-analytics-level-3 polygon,
        svg.is-analytics-bottleneck g.node.is-analytics-level-3 ellipse {
          fill: oklch(73% 0.13 64) !important;
          stroke: oklch(38% 0.13 48) !important;
          stroke-width: 2.8px !important;
        }
        svg.is-analytics-bottleneck g.node.is-analytics-level-4 {
          filter: drop-shadow(0 0 7px oklch(60% 0.16 48 / 0.32));
        }
        svg.is-analytics-bottleneck g.node.is-analytics-level-4 path,
        svg.is-analytics-bottleneck g.node.is-analytics-level-4 polygon,
        svg.is-analytics-bottleneck g.node.is-analytics-level-4 ellipse {
          fill: oklch(60% 0.16 48) !important;
          stroke: oklch(30% 0.12 42) !important;
          stroke-width: 3.4px !important;
        }
        svg.is-analytics-delay g.node.is-analytics-level-1 path,
        svg.is-analytics-delay g.node.is-analytics-level-1 polygon,
        svg.is-analytics-delay g.node.is-analytics-level-1 ellipse {
          fill: oklch(92% 0.04 245) !important;
          stroke: oklch(50% 0.09 252) !important;
          stroke-width: 1.8px !important;
        }
        svg.is-analytics-delay g.node.is-analytics-level-2 path,
        svg.is-analytics-delay g.node.is-analytics-level-2 polygon,
        svg.is-analytics-delay g.node.is-analytics-level-2 ellipse {
          fill: oklch(82% 0.07 255) !important;
          stroke: oklch(45% 0.11 260) !important;
          stroke-width: 2.2px !important;
        }
        svg.is-analytics-delay g.node.is-analytics-level-3 path,
        svg.is-analytics-delay g.node.is-analytics-level-3 polygon,
        svg.is-analytics-delay g.node.is-analytics-level-3 ellipse {
          fill: oklch(70% 0.11 270) !important;
          stroke: oklch(37% 0.13 275) !important;
          stroke-width: 2.8px !important;
        }
        svg.is-analytics-delay g.node.is-analytics-level-4 {
          filter: drop-shadow(0 0 7px oklch(58% 0.15 286 / 0.32));
        }
        svg.is-analytics-delay g.node.is-analytics-level-4 path,
        svg.is-analytics-delay g.node.is-analytics-level-4 polygon,
        svg.is-analytics-delay g.node.is-analytics-level-4 ellipse {
          fill: oklch(58% 0.15 286) !important;
          stroke: oklch(30% 0.13 286) !important;
          stroke-width: 3.4px !important;
        }
        g.node.is-analytics-themed path,
        g.node.is-analytics-themed polygon,
        g.node.is-analytics-themed ellipse {
          stroke: #40515b !important;
          stroke-width: 1.8px !important;
        }
        g.node.is-analytics-year-coded path,
        g.node.is-analytics-year-coded polygon,
        g.node.is-analytics-year-coded ellipse {
          stroke: #40515b !important;
          stroke-width: 2px !important;
        }
        g.node.is-analytics-path path,
        g.node.is-analytics-path polygon,
        g.node.is-analytics-path ellipse {
          stroke: oklch(28% 0.06 80) !important;
          stroke-width: 3.2px !important;
        }
        g.node.is-analytics-flag path,
        g.node.is-analytics-flag polygon,
        g.node.is-analytics-flag ellipse {
          fill: oklch(87% 0.11 82) !important;
          stroke: oklch(45% 0.12 52) !important;
          stroke-width: 3px !important;
        }
      `;
      svg.appendChild(style);
    };

    const getDirectTitle = (element) =>
      Array.from(element.children)
        .find((child) => child.tagName.toLowerCase() === "title")
        ?.textContent.trim() || "";

    const isCourseNodeId = (nodeId) => nodeId.startsWith("course__");

    const getNodeVisibleLines = (node) =>
      Array.from(node.querySelectorAll("text"))
        .map((text) => text.textContent.trim())
        .filter(Boolean);

    const getNodeLinkTitle = (node) => {
      const link = node.querySelector("a");
      return (
        link?.getAttribute("xlink:title") ||
        link?.getAttributeNS?.("http://www.w3.org/1999/xlink", "title") ||
        link?.getAttribute("title") ||
        ""
      );
    };

    const getNodeSearchText = (node) =>
      [getDirectTitle(node), ...getNodeVisibleLines(node), getNodeLinkTitle(node)].join(" ").toLowerCase();

    const buildGraphIndex = (svg) => {
      const nodeMap = new Map();
      const incoming = new Map();
      const outgoing = new Map();
      const edges = [];

      Array.from(svg.querySelectorAll("g.node")).forEach((node) => {
        const nodeId = getDirectTitle(node);
        if (!nodeId) {
          return;
        }
        node.dataset.atlasNodeId = nodeId;
        nodeMap.set(nodeId, node);
      });

      Array.from(svg.querySelectorAll("g.edge")).forEach((edge) => {
        const title = getDirectTitle(edge);
        const [from, to] = title.split("->");
        if (!from || !to) {
          return;
        }
        const record = { edge, from, to };
        edges.push(record);
        if (!outgoing.has(from)) {
          outgoing.set(from, []);
        }
        if (!incoming.has(to)) {
          incoming.set(to, []);
        }
        outgoing.get(from).push(record);
        incoming.get(to).push(record);
      });

      return { nodeMap, incoming, outgoing, edges };
    };

    const getActiveGraphModeKey = () => graphStage.dataset.graphMode || "simplified";

    const getActiveAnalyticsModeData = () => {
      if (!analyticsData?.modes) {
        return null;
      }
      return analyticsData.modes[getActiveGraphModeKey()] || analyticsData.modes.simplified || analyticsData.modes.full || null;
    };

    const formatAnalyticsItems = (items, formatter) => {
      if (!items || items.length === 0) {
        return "none detected";
      }
      return items.slice(0, 3).map(formatter).join(", ");
    };

    const updateAnalyticsSummary = (modeData) => {
      if (!analyticsSummary || !modeData?.metrics) {
        return;
      }
      const topText = formatAnalyticsItems(
        modeData.topBottlenecks,
        (item) => `${item.label} (${item.blockingFactor})`,
      );
      analyticsSummary.textContent = `${modeData.metrics.seosNodes} SEOS course nodes inside ${modeData.metrics.nodes} total graph nodes. SEOS bottlenecks: ${topText}.`;
    };

    const clearAnalyticsLegend = () => {
      if (!overlayLegend) {
        return;
      }
      overlayLegend.hidden = true;
      if ("open" in overlayLegend) {
        overlayLegend.open = false;
      }
      if (overlayLegendSummary) {
        overlayLegendSummary.textContent = "Legend";
        overlayLegendSummary.removeAttribute("title");
        overlayLegendSummary.removeAttribute("aria-label");
      }
      overlayLegendBody?.replaceChildren();
    };

    const appendAnalyticsLegendItem = (list, item) => {
      const row = document.createElement("div");
      row.className = "graph-overlay-legend__item";

      const swatch = document.createElement("span");
      swatch.className = "graph-overlay-legend__swatch";
      swatch.style.setProperty("--legend-color", item.color);
      if (item.borderColor) {
        swatch.style.setProperty("--legend-border", item.borderColor);
      }

      const copy = document.createElement("span");
      copy.className = "graph-overlay-legend__copy";

      const label = document.createElement("span");
      label.className = "graph-overlay-legend__label";
      label.textContent = item.label;
      copy.appendChild(label);

      if (item.detail) {
        const detail = document.createElement("span");
        detail.className = "graph-overlay-legend__detail";
        detail.textContent = item.detail;
        copy.appendChild(detail);
      }

      row.append(swatch, copy);
      list.appendChild(row);
    };

    const setAnalyticsLegend = ({ title, items }) => {
      if (!overlayLegend || !items?.length) {
        clearAnalyticsLegend();
        return;
      }

      overlayLegendBody?.replaceChildren();

      if (overlayLegendSummary) {
        overlayLegendSummary.textContent = "Legend";
        overlayLegendSummary.setAttribute("title", title);
        overlayLegendSummary.setAttribute("aria-label", `Open ${title} legend`);
      }

      const list = document.createElement("div");
      list.className = "graph-overlay-legend__list";
      items.forEach((item) => appendAnalyticsLegendItem(list, item));
      overlayLegendBody?.appendChild(list);
      overlayLegend.hidden = false;
    };

    const setBaseLegend = ({ items }) => {
      if (!overlayLegend || !items?.length) {
        clearAnalyticsLegend();
        return;
      }

      overlayLegendBody?.replaceChildren();

      if (overlayLegendSummary) {
        overlayLegendSummary.textContent = "Legend";
        overlayLegendSummary.setAttribute("title", "Graph legend");
        overlayLegendSummary.setAttribute("aria-label", "Open graph legend");
      }

      const list = document.createElement("div");
      list.className = "graph-overlay-legend__list";
      items.forEach((item) => appendAnalyticsLegendItem(list, item));
      overlayLegendBody?.appendChild(list);
      overlayLegend.hidden = false;
    };

    const showBaseLegend = () => {
      if (baseLegendData) {
        setBaseLegend(baseLegendData);
      } else {
        clearAnalyticsLegend();
      }
    };

    const buildThemeLegendItems = (modeData) => {
      const themeCounts = modeData?.themeCounts || {};
      const paletteByToken = new Map((analyticsData?.themePalette || []).map((item) => [item.token, item]));
      return Object.entries(themeCounts).map(([token, countRecord]) => {
        const paletteRecord = paletteByToken.get(token) || {};
        const count = countRecord.count || 0;
        return {
          label: countRecord.label || paletteRecord.label || token,
          detail: `${count} node${count === 1 ? "" : "s"}`,
          color: countRecord.color || paletteRecord.color || "oklch(72% 0.03 85)",
        };
      });
    };

    const buildYearLegendItems = (modeData) => {
      const yearCounts = modeData?.yearCounts || {};
      return analyticsLayerPalette.year.map((item) => {
        const count = yearCounts[item.token]?.count || 0;
        return {
          ...item,
          detail: `${item.detail}; ${count} visible node${count === 1 ? "" : "s"}`,
        };
      });
    };

    const getYearColor = (token) =>
      analyticsLayerPalette.year.find((item) => item.token === token)?.color || "";

    const updateAnalyticsLegend = (modeData) => {
      if (!modeData || activeAnalyticsMode === "base") {
        showBaseLegend();
        return;
      }

      if (activeAnalyticsMode === "bottleneck") {
        setAnalyticsLegend({
          title: "SEOS Bottleneck Scale",
          items: analyticsLayerPalette.bottleneck,
        });
      } else if (activeAnalyticsMode === "year") {
        setAnalyticsLegend({
          title: "Program Year",
          items: buildYearLegendItems(modeData),
        });
      } else if (activeAnalyticsMode === "delay") {
        setAnalyticsLegend({
          title: "Prerequisite Chain Depth",
          items: analyticsLayerPalette.delay,
        });
      } else if (activeAnalyticsMode === "theme") {
        setAnalyticsLegend({
          title: "Subject Themes",
          items: buildThemeLegendItems(modeData),
        });
      } else if (activeAnalyticsMode === "cleanup") {
        setAnalyticsLegend({
          title: "Cleanup Flags",
          items: analyticsLayerPalette.cleanup,
        });
      } else {
        clearAnalyticsLegend();
      }
    };

    const clearAnalyticsOverlay = (svg, graphIndex) => {
      if (!svg || !graphIndex) {
        return;
      }
      svg.classList.remove(
        "atlas-analytics-active",
        "is-analytics-bottleneck",
        "is-analytics-delay",
        "is-analytics-year",
        "is-analytics-theme",
        "is-analytics-cleanup",
      );
      graphIndex.nodeMap.forEach((node) => {
        node.classList.remove(
          "analytics-muted",
          "is-analytics-level-1",
          "is-analytics-level-2",
          "is-analytics-level-3",
          "is-analytics-level-4",
          "is-analytics-themed",
          "is-analytics-year-coded",
          "is-analytics-path",
          "is-analytics-flag",
        );
        node.querySelectorAll("path, polygon, ellipse").forEach((shape) => {
          shape.style.removeProperty("fill");
          shape.style.removeProperty("stroke");
          shape.style.removeProperty("stroke-width");
        });
      });
      graphIndex.edges.forEach(({ edge }) => edge.classList.remove("is-analytics-path"));
    };

    const applyAnalyticsOverlay = (svg = getActiveSvg()) => {
      if (!svg || !analyticsData) {
        showBaseLegend();
        return;
      }
      prepareGraphSvg(svg);
      const modeData = getActiveAnalyticsModeData();
      const graphIndex = buildGraphIndex(svg);
      clearAnalyticsOverlay(svg, graphIndex);
      updateAnalyticsSummary(modeData);
      updateAnalyticsLegend(modeData);

      if (!modeData || activeAnalyticsMode === "base") {
        return;
      }

      const analyticsNodes = new Map((modeData.nodes || []).map((node) => [node.id, node]));
      svg.classList.add("atlas-analytics-active", `is-analytics-${activeAnalyticsMode}`);

      graphIndex.nodeMap.forEach((node, nodeId) => {
        const record = analyticsNodes.get(nodeId);
        if (!record) {
          node.classList.add("analytics-muted");
          return;
        }

        if (activeAnalyticsMode === "bottleneck" || activeAnalyticsMode === "delay") {
          const levelKey = activeAnalyticsMode === "bottleneck" ? "blocking" : "delay";
          const level = record.levels?.[levelKey] || 0;
          if (level > 0) {
            node.classList.add(`is-analytics-level-${level}`);
          } else {
            node.classList.add("analytics-muted");
          }
          if (
            (activeAnalyticsMode === "bottleneck" && record.onLongestPath) ||
            (activeAnalyticsMode === "delay" && record.onDeepestPrerequisiteChain)
          ) {
            node.classList.add("is-analytics-path");
          }
        }

        if (activeAnalyticsMode === "theme") {
          const color = record.themeColor;
          if (!color) {
            node.classList.add("analytics-muted");
            return;
          }
          node.classList.add("is-analytics-themed");
          node.querySelectorAll("path, polygon, ellipse").forEach((shape) => {
            shape.style.setProperty("fill", color);
          });
        }

        if (activeAnalyticsMode === "year") {
          const color = getYearColor(record.year);
          if (!color) {
            node.classList.add("analytics-muted");
            return;
          }
          node.classList.add("is-analytics-year-coded");
          node.querySelectorAll("path, polygon, ellipse").forEach((shape) => {
            shape.style.setProperty("fill", color);
          });
        }
      });

      if (activeAnalyticsMode === "cleanup") {
        const flaggedIds = new Set();
        (modeData.redundantPrerequisites || []).forEach((check) => {
          flaggedIds.add(`course__${check.courseGroup}`);
        });
        graphIndex.nodeMap.forEach((node, nodeId) => {
          if (flaggedIds.has(nodeId)) {
            node.classList.add("is-analytics-flag");
          } else {
            node.classList.add("analytics-muted");
          }
        });
      }

    };

    const collectBranchContext = (index, matchedNodes) => {
      const contextNodes = new Set(matchedNodes);
      const terminalNodes = new Set();
      const branchEdges = new Set();
      const queue = [];
      const visited = new Set();

      const enqueue = (nodeId, direction, originId) => {
        const edgeRecords = direction === "out" ? index.outgoing.get(nodeId) || [] : index.incoming.get(nodeId) || [];
        edgeRecords.forEach((record) => {
          const key = `${direction}:${originId}:${record.from}->${record.to}`;
          if (visited.has(key)) {
            return;
          }
          visited.add(key);
          queue.push({ record, direction, originId });
        });
      };

      matchedNodes.forEach((node) => {
        const nodeId = node.dataset.atlasNodeId || getDirectTitle(node);
        if (!nodeId) {
          return;
        }
        enqueue(nodeId, "in", nodeId);
        enqueue(nodeId, "out", nodeId);
      });

      while (queue.length > 0) {
        const { record, direction, originId } = queue.shift();
        const nextId = direction === "out" ? record.to : record.from;
        const nextNode = index.nodeMap.get(nextId);

        branchEdges.add(record.edge);
        if (!nextNode) {
          continue;
        }

        contextNodes.add(nextNode);
        if (nextId !== originId && isCourseNodeId(nextId)) {
          terminalNodes.add(nextNode);
          continue;
        }

        enqueue(nextId, direction, originId);
      }

      return { contextNodes, terminalNodes, branchEdges };
    };

    const hideGraphAutocomplete = () => {
      if (!autocompletePanel) {
        return;
      }
      autocompletePanel.hidden = true;
      autocompletePanel.replaceChildren();
      activeAutocompleteIndex = -1;
      graphSearchInput?.removeAttribute("aria-activedescendant");
    };

    const setActiveAutocompleteOption = (index) => {
      const options = Array.from(autocompletePanel.querySelectorAll("[data-graph-autocomplete-option]"));
      if (options.length === 0) {
        activeAutocompleteIndex = -1;
        return;
      }
      activeAutocompleteIndex = Math.max(0, Math.min(index, options.length - 1));
      options.forEach((option, optionIndex) => {
        const isActive = optionIndex === activeAutocompleteIndex;
        option.classList.toggle("is-active", isActive);
        option.setAttribute("aria-selected", String(isActive));
      });
      graphSearchInput?.setAttribute("aria-activedescendant", options[activeAutocompleteIndex]?.id || "");
      options[activeAutocompleteIndex]?.scrollIntoView({ block: "nearest" });
    };

    const selectAutocompleteOption = (option) => {
      if (!graphSearchInput || !option) {
        return;
      }
      graphSearchInput.value = option.value;
      hideGraphAutocomplete();
      updateGraphSearch();
      graphSearchInput.focus();
    };

    const renderGraphAutocomplete = () => {
      if (!graphSearchInput || !autocompletePanel) {
        return;
      }

      const query = graphSearchInput.value.trim().toLowerCase();
      if (!query) {
        hideGraphAutocomplete();
        return;
      }

      const matches = graphAutocompleteOptions
        .filter((option) => option.searchText.includes(query))
        .slice(0, 8);

      if (matches.length === 0) {
        hideGraphAutocomplete();
        return;
      }

      autocompletePanel.replaceChildren(
        ...matches.map((option, index) => {
          const button = document.createElement("button");
          button.className = "graph-search-autocomplete__option";
          button.type = "button";
          button.id = `${autocompletePanel.id}-option-${index}`;
          button.setAttribute("role", "option");
          button.setAttribute("aria-selected", "false");
          button.dataset.graphAutocompleteOption = "true";
          button.setAttribute("aria-label", option.label ? `${option.value}: ${option.label}` : option.value);

          const value = document.createElement("span");
          value.className = "graph-search-autocomplete__value";
          value.textContent = option.value;
          button.appendChild(value);

          if (option.label) {
            const detail = document.createElement("span");
            detail.className = "graph-search-autocomplete__detail";
            detail.textContent = option.label;
            button.appendChild(detail);
          }

          button.addEventListener("pointerdown", (event) => {
            event.preventDefault();
          });
          button.addEventListener("mouseenter", () => setActiveAutocompleteOption(index));
          button.addEventListener("click", () => selectAutocompleteOption(option));
          return button;
        }),
      );

      autocompletePanel.hidden = false;
      setActiveAutocompleteOption(0);
    };

    const updateGraphAutocomplete = (svg) => {
      if (!graphSearchInput) {
        return;
      }

      graphAutocompleteOptions = Array.from(svg.querySelectorAll("g.node"))
        .map((node) => {
          const nodeId = getDirectTitle(node);
          if (!isCourseNodeId(nodeId)) {
            return null;
          }
          const visibleLines = getNodeVisibleLines(node);
          const value = visibleLines[0] || nodeId.replace(/^course__/, "");
          const label = [visibleLines.slice(1).join(" "), getNodeLinkTitle(node)]
            .filter(Boolean)
            .join(" | ");
          return {
            value,
            label,
            searchText: [value, label, nodeId.replace(/^course__/, "")].filter(Boolean).join(" ").toLowerCase(),
          };
        })
        .filter(Boolean)
        .filter(
          (option, index, allOptions) =>
            allOptions.findIndex((candidate) => candidate.value === option.value) === index,
        )
        .sort((a, b) => a.value.localeCompare(b.value, undefined, { numeric: true }));

      renderGraphAutocomplete();
    };

    const getNodePrimaryLabel = (node) => {
      const nodeId = node.dataset.atlasNodeId || getDirectTitle(node);
      return getNodeVisibleLines(node)[0] || nodeId.replace(/^course__/, "");
    };

    const clearGraphHighlight = (svg, graphIndex) => {
      svg.classList.remove("atlas-searching");
      svg.dataset.atlasSelectedNodeId = "";
      graphIndex.nodeMap.forEach((node) => {
        node.classList.remove("is-atlas-match", "is-atlas-context", "is-atlas-terminal");
      });
      graphIndex.edges.forEach(({ edge }) => edge.classList.remove("is-atlas-branch"));
    };

    const highlightGraphNodes = (svg, graphIndex, matchedNodes, options = {}) => {
      const focus = options.focus ?? true;
      clearGraphHighlight(svg, graphIndex);
      if (matchedNodes.length === 0) {
        if (focus) {
          restoreGraphView(svg);
        }
        return { branchCount: 0 };
      }

      svg.classList.add("atlas-searching");
      const branchContext = collectBranchContext(graphIndex, matchedNodes);
      matchedNodes.forEach((node) => node.classList.add("is-atlas-match", "is-atlas-context"));
      branchContext.contextNodes.forEach((node) => node.classList.add("is-atlas-context"));
      branchContext.terminalNodes.forEach((node) => node.classList.add("is-atlas-terminal"));
      branchContext.branchEdges.forEach((edge) => edge.classList.add("is-atlas-branch"));
      if (focus) {
        const focusElements = document.body.classList.contains("page--secret-computing")
          ? matchedNodes
          : [...branchContext.contextNodes, ...branchContext.branchEdges];
        focusGraphElements(svg, focusElements);
      }
      return { branchCount: branchContext.branchEdges.size };
    };

    const getLinkHref = (link) =>
      link?.getAttribute("href") ||
      link?.getAttribute("xlink:href") ||
      link?.getAttributeNS?.("http://www.w3.org/1999/xlink", "href") ||
      "";

    const isModifiedActivation = (event) =>
      event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey;

    const prepareGraphSvg = (svg) => {
      if (!svg || svg.dataset.atlasGraphReady === "true") {
        return;
      }

      svg.dataset.atlasGraphReady = "true";
      svg.classList.add("atlas-graph-svg");
      svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
      getDefaultViewBox(svg);
      injectGraphSearchStyles(svg);
      updateGraphAutocomplete(svg);

      let dragState = null;
      let suppressNextClick = false;

      svg.addEventListener(
        "wheel",
        (event) => {
          event.preventDefault();
          zoomGraph(svg, event.deltaY < 0 ? 0.84 : 1.18, event.clientX, event.clientY);
        },
        { passive: false },
      );

      svg.addEventListener("pointerdown", (event) => {
        if (event.button !== 0) {
          return;
        }
        dragState = {
          lastX: event.clientX,
          lastY: event.clientY,
          startX: event.clientX,
          startY: event.clientY,
          moved: false,
          pointerId: event.pointerId,
        };
      });

      svg.addEventListener("pointermove", (event) => {
        if (!dragState) {
          return;
        }

        const totalMove = Math.hypot(event.clientX - dragState.startX, event.clientY - dragState.startY);
        if (!dragState.moved && totalMove < 4) {
          return;
        }

        if (!dragState.moved) {
          dragState.moved = true;
          suppressNextClick = true;
          svg.classList.add("is-atlas-panning");
          svg.setPointerCapture?.(dragState.pointerId);
        }

        event.preventDefault();
        const current = getCurrentViewBox(svg);
        const rect = svg.getBoundingClientRect();
        if (!current || rect.width === 0 || rect.height === 0) {
          return;
        }

        const deltaX = ((event.clientX - dragState.lastX) * current.width) / rect.width;
        const deltaY = ((event.clientY - dragState.lastY) * current.height) / rect.height;
        dragState.lastX = event.clientX;
        dragState.lastY = event.clientY;
        setViewBox(svg, {
          ...current,
          x: current.x - deltaX,
          y: current.y - deltaY,
        });
      });

      const endDrag = () => {
        if (!dragState) {
          return;
        }
        svg.classList.remove("is-atlas-panning");
        svg.releasePointerCapture?.(dragState.pointerId);
        dragState = null;
      };

      svg.addEventListener("pointerup", endDrag);
      svg.addEventListener("pointercancel", endDrag);
      svg.addEventListener(
        "click",
        (event) => {
          if (!suppressNextClick) {
            return;
          }
          event.preventDefault();
          event.stopImmediatePropagation();
          suppressNextClick = false;
        },
        true,
      );

      svg.addEventListener(
        "click",
        (event) => {
          if (suppressNextClick || isModifiedActivation(event)) {
            return;
          }

          const link = event.target.closest?.("a");
          const node = event.target.closest?.("g.node");
          const href = getLinkHref(link);
          if (!document.body.classList.contains("page--program-detail")) {
            return;
          }

          const graphIndex = buildGraphIndex(svg);
          if (!node) {
            if (svg.dataset.atlasSelectedNodeId || svg.classList.contains("atlas-searching")) {
              event.preventDefault();
              event.stopPropagation();
              clearGraphHighlight(svg, graphIndex);
              restoreGraphView(svg);
              if (graphSearchInput) {
                graphSearchInput.value = "";
              }
              hideGraphAutocomplete();
              if (graphSearchStatus) {
                graphSearchStatus.textContent =
                  "Search highlights the matched course and its connected prerequisite branches. Scroll to zoom, drag to pan.";
              }
            }
            return;
          }

          if (!link || !href) {
            return;
          }

          const nodeId = node.dataset.atlasNodeId || getDirectTitle(node);
          const selectedNodeId = svg.dataset.atlasSelectedNodeId || "";
          if (
            nodeId &&
            node.classList.contains("is-atlas-match") &&
            (!selectedNodeId || selectedNodeId === nodeId)
          ) {
            return;
          }

          event.preventDefault();
          event.stopPropagation();
          const { branchCount } = highlightGraphNodes(svg, graphIndex, [node]);
          svg.dataset.atlasSelectedNodeId = nodeId;
          if (graphSearchInput) {
            graphSearchInput.value = getNodePrimaryLabel(node);
          }
          if (graphSearchStatus) {
            graphSearchStatus.textContent = `${getNodePrimaryLabel(node)} highlighted with ${branchCount} connected branch${branchCount === 1 ? "" : "es"}. Select it again to open the course page.`;
          }
        },
        true,
      );
    };

    const updateGraphSearch = () => {
      const query = (graphSearchInput?.value || "").trim().toLowerCase();
      const svg = getActiveSvg();
      if (!svg) {
        if (graphSearchStatus) {
          graphSearchStatus.textContent = "Search is available after the graph finishes loading.";
        }
        return;
      }

      prepareGraphSvg(svg);
      const graphIndex = buildGraphIndex(svg);
      const nodes = Array.from(graphIndex.nodeMap.values());
      let matchCount = 0;
      const matchedNodes = [];

      nodes.forEach((node) => {
        const text = getNodeSearchText(node);
        const isMatch = Boolean(query) && text.includes(query);
        if (isMatch) {
          matchCount += 1;
          matchedNodes.push(node);
        }
      });

      if (!query || matchedNodes.length === 0) {
        clearGraphHighlight(svg, graphIndex);
        restoreGraphView(svg);
      } else {
        svg.dataset.atlasSelectedNodeId = "";
        highlightGraphNodes(svg, graphIndex, matchedNodes);
      }

      if (!graphSearchStatus) {
        return;
      }
      if (!query) {
        graphSearchStatus.textContent =
          "Search highlights the matched course and its connected prerequisite branches. Scroll to zoom, drag to pan.";
      } else if (matchCount === 0) {
        graphSearchStatus.textContent = `No graph nodes match "${graphSearchInput.value}".`;
      } else {
        const branchCount = svg.querySelectorAll("g.edge.is-atlas-branch").length;
        graphSearchStatus.textContent = `${matchCount} matching graph node${matchCount === 1 ? "" : "s"} with ${branchCount} connected branch${branchCount === 1 ? "" : "es"} highlighted.`;
      }
    };

    const applyMode = (button) => {
      const modeKey = button.getAttribute("data-graph-mode");
      const download = button.getAttribute("data-graph-download") || button.getAttribute("data-graph-src");
      const copy = button.getAttribute("data-graph-copy") || "";
      const template = templates.find((candidate) => candidate.getAttribute("data-graph-template") === modeKey);

      if (template) {
        const svg = template.content.firstElementChild?.cloneNode(true);
        if (svg) {
          graphStage.replaceChildren(svg);
          graphStage.dataset.graphMode = modeKey || "";
          prepareGraphSvg(svg);
          applyAnalyticsOverlay(svg);
        }
      }

      if (graphLink && download) {
        graphLink.setAttribute("href", download);
      }

      if (modeCopy) {
        modeCopy.textContent = copy;
      }

      buttons.forEach((candidate) => {
        const isActive = candidate === button;
        candidate.classList.toggle("is-active", isActive);
        candidate.setAttribute("aria-pressed", String(isActive));
      });

      updateGraphSearch();
      applyAnalyticsOverlay();
    };

    buttons.forEach((button) => {
      button.addEventListener("click", () => applyMode(button));
    });

    if (graphSearchInput) {
      graphSearchInput.addEventListener("input", () => {
        updateGraphSearch();
        renderGraphAutocomplete();
      });
      graphSearchInput.addEventListener("focus", renderGraphAutocomplete);
      graphSearchInput.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
          hideGraphAutocomplete();
          return;
        }

        const options = Array.from(autocompletePanel.querySelectorAll("[data-graph-autocomplete-option]"));
        if ((event.key === "ArrowDown" || event.key === "ArrowUp") && autocompletePanel.hidden) {
          renderGraphAutocomplete();
        }

        if (event.key === "ArrowDown") {
          event.preventDefault();
          setActiveAutocompleteOption(activeAutocompleteIndex + 1);
        } else if (event.key === "ArrowUp") {
          event.preventDefault();
          setActiveAutocompleteOption(activeAutocompleteIndex - 1);
        } else if (event.key === "Enter" && options[activeAutocompleteIndex]) {
          event.preventDefault();
          options[activeAutocompleteIndex].click();
        }
      });
      document.addEventListener("pointerdown", (event) => {
        if (graphSearchDockBody?.contains(event.target)) {
          return;
        }
        hideGraphAutocomplete();
      });
    }

    if (resetButton) {
      resetButton.addEventListener("click", () => {
        if (graphSearchInput) {
          graphSearchInput.value = "";
        }
        hideGraphAutocomplete();
        restoreGraphView();
        updateGraphSearch();
        applyAnalyticsOverlay();
      });
    }

    const setActiveAnalyticsMode = (mode) => {
      activeAnalyticsMode = mode || "base";
      if (analyticsSelect && analyticsSelect.value !== activeAnalyticsMode) {
        analyticsSelect.value = activeAnalyticsMode;
      }
      analyticsButtons.forEach((candidate) => {
        const isActive = (candidate.getAttribute("data-analytics-mode") || "base") === activeAnalyticsMode;
        candidate.classList.toggle("is-active", isActive);
        candidate.setAttribute("aria-pressed", String(isActive));
      });
      applyAnalyticsOverlay();
    };

    analyticsButtons.forEach((button) => {
      button.addEventListener("click", () => {
        setActiveAnalyticsMode(button.getAttribute("data-analytics-mode") || "base");
      });
    });

    if (analyticsSelect) {
      analyticsSelect.addEventListener("change", () => {
        setActiveAnalyticsMode(analyticsSelect.value || "base");
      });
    }

    const activeButton = buttons.find((button) => button.classList.contains("is-active")) || buttons[0];
    applyMode(activeButton);
  });
});
