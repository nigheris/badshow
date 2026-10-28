(() => {
  const chartSection = document.querySelector("[data-market-chart]");
  if (!chartSection) return;

  if (typeof Chart === "undefined") {
    const status = chartSection.querySelector("[data-market-state]");
    const price = chartSection.querySelector("[data-market-price]");
    const change = chartSection.querySelector("[data-market-change]");
    status.textContent = "The interactive chart is unavailable. Please try again later.";
    price.textContent = "Chart unavailable";
    change.textContent = "";
    return;
  }

  const assets = {
    bitcoin: { name: "Bitcoin", symbol: "BTC" },
    ethereum: { name: "Ethereum", symbol: "ETH" },
    "usd-coin": { name: "USD Coin", symbol: "USDC" },
    solana: { name: "Solana", symbol: "SOL" },
    tether: { name: "Tether", symbol: "USDT" },
    ripple: { name: "XRP", symbol: "XRP" },
  };
  const periods = {
    1: { label: "1D", interval: "hour" },
    7: { label: "1W", interval: "day" },
    30: { label: "1M", interval: "day" },
    365: { label: "1Y", interval: "day" },
  };
  const canvas = chartSection.querySelector("[data-market-canvas]");
  const status = chartSection.querySelector("[data-market-state]");
  const nameNode = chartSection.querySelector("[data-market-name]");
  const pairNode = chartSection.querySelector("[data-market-pair]");
  const priceNode = chartSection.querySelector("[data-market-price]");
  const changeNode = chartSection.querySelector("[data-market-change]");
  const updatedNode = chartSection.querySelector("[data-market-updated]");
  const assetButtons = Array.from(chartSection.querySelectorAll("[data-asset]"));
  const periodButtons = Array.from(chartSection.querySelectorAll("[data-days]"));
  const refreshButton = chartSection.querySelector("[data-market-refresh]");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  let selectedAsset = "bitcoin";
  let selectedDays = 1;
  let activeRequest;
  let requestSequence = 0;
  let priceChart;

  function formatPrice(value) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: value < 1 ? 4 : 2,
      maximumFractionDigits: value < 1 ? 4 : 2,
    }).format(value);
  }

  function formatAxisPrice(value) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      notation: "compact",
      maximumFractionDigits: 2,
    }).format(value);
  }

  function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    if (selectedDays === 1) {
      return date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
    }
    if (selectedDays === 7) {
      return date.toLocaleDateString("en-US", { weekday: "short", hour: "numeric" });
    }
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  function setLoading(message) {
    status.textContent = message;
    status.hidden = false;
    priceNode.textContent = "Loading market data...";
    changeNode.textContent = "Fetching latest history";
    changeNode.classList.remove("is-positive", "is-negative");
  }

  function showError() {
    priceNode.textContent = "Market data unavailable";
    changeNode.textContent = "Try refreshing in a moment";
    changeNode.classList.remove("is-positive", "is-negative");
    status.textContent = "Live market data is temporarily unavailable. Please try again shortly.";
    status.hidden = false;
    updatedNode.textContent = "Market history is supplied by CoinGecko.";
  }

  function renderChart(prices) {
    if (priceChart) priceChart.destroy();

    const chartContext = canvas.getContext("2d");
    const fill = chartContext.createLinearGradient(0, 0, 0, 320);
    fill.addColorStop(0, "rgba(62, 128, 255, 0.18)");
    fill.addColorStop(1, "rgba(62, 128, 255, 0.01)");

    priceChart = new Chart(chartContext, {
      type: "line",
      data: {
        labels: prices.map(([timestamp]) => formatTimestamp(timestamp)),
        datasets: [{
          data: prices.map(([, price]) => price),
          borderColor: "#3e80ff",
          backgroundColor: fill,
          borderWidth: 2,
          fill: true,
          pointRadius: 0,
          pointHoverRadius: 4,
          pointHoverBackgroundColor: "#24126a",
          tension: 0.22,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: reducedMotion ? false : { duration: 250 },
        interaction: { intersect: false, mode: "index" },
        plugins: {
          legend: { display: false },
          tooltip: {
            displayColors: false,
            callbacks: {
              label: (context) => formatPrice(context.parsed.y),
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            border: { display: false },
            ticks: {
              color: "#8792a3",
              maxTicksLimit: 7,
              maxRotation: 0,
              autoSkip: true,
              font: { size: 10 },
            },
          },
          y: {
            position: "right",
            border: { display: false },
            grid: { color: "#edf0f4" },
            ticks: {
              color: "#8792a3",
              maxTicksLimit: 5,
              padding: 10,
              callback: formatAxisPrice,
              font: { size: 10 },
            },
          },
        },
      },
    });
  }

  async function loadMarketData() {
    const sequence = ++requestSequence;
    if (activeRequest) activeRequest.abort();
    activeRequest = new AbortController();

    const asset = assets[selectedAsset];
    const period = periods[selectedDays];
    nameNode.textContent = asset.name;
    pairNode.textContent = `${asset.symbol} / USD`;
    canvas.setAttribute("aria-label", `${asset.name} price history in US dollars`);
    setLoading(`Loading ${asset.name} market history...`);

    const query = new URLSearchParams({ vs_currency: "usd", days: String(selectedDays) });
    if (period.interval === "day" && selectedDays === 365) query.set("interval", "daily");
    const url = `https://api.coingecko.com/api/v3/coins/${selectedAsset}/market_chart?${query}`;

    try {
      const response = await fetch(url, {
        signal: activeRequest.signal,
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error("Market data request failed");

      const result = await response.json();
      if (sequence !== requestSequence) return;
      const prices = Array.isArray(result.prices)
        ? result.prices.filter((entry) => Array.isArray(entry) && Number.isFinite(entry[0]) && Number.isFinite(entry[1]))
        : [];
      if (!prices.length) throw new Error("No market history returned");

      const firstPrice = prices[0][1];
      const lastPrice = prices[prices.length - 1][1];
      const percentageChange = firstPrice ? ((lastPrice - firstPrice) / firstPrice) * 100 : 0;
      const sign = percentageChange > 0 ? "+" : "";

      priceNode.textContent = formatPrice(lastPrice);
      changeNode.textContent = `${sign}${percentageChange.toFixed(2)}% over ${period.label}`;
      changeNode.classList.toggle("is-positive", percentageChange >= 0);
      changeNode.classList.toggle("is-negative", percentageChange < 0);
      updatedNode.textContent = `CoinGecko market history · Updated ${new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}`;
      status.hidden = true;
      renderChart(prices);
    } catch (error) {
      if (error.name === "AbortError" || sequence !== requestSequence) return;
      showError();
    }
  }

  assetButtons.forEach((button) => {
    button.addEventListener("click", () => {
      selectedAsset = button.dataset.asset;
      assetButtons.forEach((item) => {
        const isSelected = item === button;
        item.classList.toggle("is-selected", isSelected);
        item.setAttribute("aria-pressed", String(isSelected));
      });
      loadMarketData();
    });
  });

  periodButtons.forEach((button) => {
    button.addEventListener("click", () => {
      selectedDays = Number(button.dataset.days);
      periodButtons.forEach((item) => {
        const isSelected = item === button;
        item.classList.toggle("is-selected", isSelected);
        item.setAttribute("aria-pressed", String(isSelected));
      });
      loadMarketData();
    });
  });

  refreshButton.addEventListener("click", loadMarketData);
  loadMarketData();
})();