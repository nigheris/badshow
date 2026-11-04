import { useEffect, useState } from "react";
import {
  Activity,
  ArrowDownLeft,
  ArrowRight,
  ArrowUpRight,
  Bookmark,
  Briefcase,
  Clock3,
  Eye,
  EyeOff,
  Landmark,
  Plus,
  RefreshCw,
  TrendingUp,
  WalletCards,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Tabs,
} from "./components/ui";
import "./dashboard.css";

const assets = {
  bitcoin: { name: "Bitcoin", symbol: "BTC" },
  ethereum: { name: "Ethereum", symbol: "ETH" },
  "usd-coin": { name: "USD Coin", symbol: "USDC" },
  solana: { name: "Solana", symbol: "SOL" },
};

const periods = [
  { label: "1W", days: 7 },
  { label: "1M", days: 30 },
  { label: "3M", days: 90 },
];

function parseAmount(value) {
  const amount = Number.parseFloat(String(value ?? "0").replace(/[^\d.-]/g, ""));
  return Number.isFinite(amount) ? amount : 0;
}

function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date unavailable";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

function statusVariant(status) {
  if (status === "credit") return "positive";
  if (status === "failed" || status === "error") return "negative";
  if (status === "pending" || status === "processing" || status === "confirming") return "warning";
  return "muted";
}

function StatCard({ label, value, detail, icon: Icon, action }) {
  return (
    <Card className="stat-card">
      <CardHeader className="stat-card-header">
        <CardDescription>{label}</CardDescription>
        <span className="stat-icon"><Icon size={17} strokeWidth={1.7} /></span>
      </CardHeader>
      <CardContent>
        <p className="stat-value">{value}</p>
        <p className="stat-detail">{detail}</p>
        {action}
      </CardContent>
    </Card>
  );
}

function MarketChart() {
  const [assetId, setAssetId] = useState("bitcoin");
  const [days, setDays] = useState(7);
  const [points, setPoints] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [chartModules, setChartModules] = useState(null);
  const [chartLoadError, setChartLoadError] = useState(false);
  const [updatedAt, setUpdatedAt] = useState(null);
  const [requestNumber, setRequestNumber] = useState(0);
  const asset = assets[assetId];
  const {
    Area,
    AreaChart,
    CartesianGrid,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
  } = chartModules || {};

  useEffect(() => {
    let active = true;

    import("recharts")
      .then((modules) => {
        if (active) setChartModules(modules);
      })
      .catch(() => {
        if (active) setChartLoadError(true);
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    async function loadHistory() {
      setIsLoading(true);
      setHasError(false);
      const query = new URLSearchParams({ vs_currency: "usd", days: String(days) });

      try {
        const response = await fetch(
          `https://api.coingecko.com/api/v3/coins/${assetId}/market_chart?${query}`,
          { signal: controller.signal, headers: { Accept: "application/json" } },
        );
        if (!response.ok) throw new Error("Market request failed");

        const result = await response.json();
        const history = Array.isArray(result.prices) ? result.prices : [];
        const step = Math.max(1, Math.ceil(history.length / 90));
        const sampled = history
          .filter((entry) => Array.isArray(entry) && Number.isFinite(entry[0]) && Number.isFinite(entry[1]))
          .filter((_, index) => index % step === 0)
          .map(([timestamp, price]) => ({
            time: timestamp,
            label: new Intl.DateTimeFormat("en-US", {
              month: "short",
              day: "numeric",
              ...(days === 7 ? { hour: "numeric" } : {}),
            }).format(new Date(timestamp)),
            price,
          }));

        if (!sampled.length) throw new Error("Market history is empty");
        if (active) {
          setPoints(sampled);
          setUpdatedAt(new Date());
        }
      } catch (error) {
        if (active && error.name !== "AbortError") {
          setHasError(true);
          setPoints([]);
        }
      } finally {
        if (active) setIsLoading(false);
      }
    }

    loadHistory();
    return () => {
      active = false;
      controller.abort();
    };
  }, [assetId, days, requestNumber]);

  const currentPrice = points.length ? points[points.length - 1].price : null;
  const firstPrice = points.length ? points[0].price : null;
  const change = firstPrice ? ((currentPrice - firstPrice) / firstPrice) * 100 : null;
  const chartColor = change !== null && change < 0 ? "#c6505f" : "#3e80ff";

  return (
    <Card className="market-card">
      <CardHeader className="market-card-header">
        <div>
          <CardTitle>Market overview</CardTitle>
          <CardDescription>Public market data · not your account performance</CardDescription>
        </div>
        <div className="market-filters">
          <label className="sr-only" htmlFor="market-asset">Choose asset</label>
          <select id="market-asset" value={assetId} onChange={(event) => setAssetId(event.target.value)}>
            {Object.entries(assets).map(([id, item]) => (
              <option value={id} key={id}>{item.symbol}</option>
            ))}
          </select>
          <div className="market-periods" role="group" aria-label="Market chart period">
            {periods.map((period) => (
              <button
                type="button"
                className={days === period.days ? "is-active" : ""}
                aria-pressed={days === period.days}
                onClick={() => setDays(period.days)}
                key={period.days}
              >
                {period.label}
              </button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="chart-price-row">
          <p className="chart-current-price">{currentPrice === null ? "--" : formatCurrency(currentPrice)}</p>
          {change !== null && (
            <Badge variant={change >= 0 ? "positive" : "negative"}>
              {change >= 0 ? "+" : ""}{change.toFixed(2)}%
            </Badge>
          )}
          {updatedAt && <span className="chart-updated">Updated {updatedAt.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}</span>}
        </div>
        <div className="chart-container" aria-label={`${asset.name} USD market history`}>
          {isLoading || (!chartModules && !chartLoadError) ? (
            <div className="chart-state" role="status">Loading market data...</div>
          ) : hasError || chartLoadError ? (
            <div className="chart-state chart-state-error" role="status">
              <span>{chartLoadError ? "The market chart could not be loaded." : "Market history is temporarily unavailable."}</span>
              {!chartLoadError && (
                <Button variant="outline" size="sm" onClick={() => setRequestNumber((number) => number + 1)}>
                  <RefreshCw size={14} /> Retry
                </Button>
              )}
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={points} margin={{ top: 10, right: 4, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id="marketFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={chartColor} stopOpacity={0.16} />
                    <stop offset="95%" stopColor={chartColor} stopOpacity={0.01} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke="#e9edf3" strokeDasharray="3 5" />
                <XAxis dataKey="label" tickLine={false} axisLine={false} minTickGap={34} tick={{ fill: "#8792a3", fontSize: 11 }} />
                <YAxis orientation="right" tickLine={false} axisLine={false} width={66} tick={{ fill: "#8792a3", fontSize: 11 }} tickFormatter={(value) => `$${Number(value).toLocaleString("en-US", { notation: "compact", maximumFractionDigits: 1 })}`} />
                <Tooltip
                  formatter={(value) => [formatCurrency(value), asset.symbol]}
                  labelStyle={{ color: "#344054", fontSize: 12 }}
                  contentStyle={{ border: "1px solid #e3e8ef", borderRadius: 8, boxShadow: "0 8px 24px rgba(20, 32, 54, 0.1)" }}
                />
                <Area type="monotone" dataKey="price" stroke={chartColor} strokeWidth={2} fill="url(#marketFill)" activeDot={{ r: 4, strokeWidth: 0 }} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
        <p className="chart-source">Source: CoinGecko. Prices can be delayed; historical data does not predict future results.</p>
      </CardContent>
    </Card>
  );
}

function TransactionTable({ transactions, compact = false }) {
  const rows = compact ? transactions.slice(0, 5) : transactions;

  if (!rows.length) {
    return <p className="empty-state">Your account activity will appear here.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Activity</TableHead>
          {!compact && <TableHead>Reference</TableHead>}
          <TableHead>Date</TableHead>
          <TableHead>Status</TableHead>
          <TableHead className="amount-cell">Amount</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((transaction) => {
          const isCredit = transaction.status === "credit";
          const amount = parseAmount(transaction.amount);
          const DirectionIcon = isCredit ? ArrowDownLeft : ArrowUpRight;
          return (
            <TableRow key={transaction.id}>
              <TableCell>
                <div className="transaction-description">
                  <span className={`transaction-icon ${isCredit ? "is-credit" : ""}`}><DirectionIcon size={15} /></span>
                  <span className="transaction-copy">
                    <strong>{transaction.msg || (isCredit ? "Account credit" : "Account transaction")}</strong>
                    <small>{isCredit ? "Incoming" : "Account activity"}</small>
                  </span>
                </div>
              </TableCell>
              {!compact && <TableCell className="transaction-reference">{transaction.transactionId || "--"}</TableCell>}
              <TableCell className="transaction-date">{formatDate(transaction.timestamp)}</TableCell>
              <TableCell><Badge variant={statusVariant(transaction.status)}>{transaction.status}</Badge></TableCell>
              <TableCell className="amount-cell">{transaction.amount ? formatCurrency(amount) : "--"}</TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

const tradeSections = [
  {
    value: "available",
    label: "Open trades",
    title: "Open trades",
    description: "Open opportunities available to join",
    icon: TrendingUp,
  },
  {
    value: "my-open",
    label: "My open trades",
    title: "Your open trades",
    description: "Your active positions",
    icon: Clock3,
  },
  {
    value: "watchlist",
    label: "Watchlist",
    title: "Trades to watch",
    description: "Open opportunities you are keeping an eye on",
    icon: Bookmark,
  },
  {
    value: "closed",
    label: "Closed trades",
    title: "Closed trades",
    description: "Your positions in closed opportunities",
    icon: Briefcase,
  },
];

function TradeActionForm({ action, actionUrl, csrfToken, tradeId, amount, children }) {
  return (
    <form method="post" action={actionUrl} className="trade-action-form">
      <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
      <input type="hidden" name="action" value={action} />
      <input type="hidden" name="trade_id" value={tradeId} />
      {amount}
      {children}
    </form>
  );
}

function TradeOpportunityTable({
  trades,
  actionUrl,
  csrfToken,
  watchlistIds,
}) {
  if (!trades.length) {
    return (
      <p className="empty-state">
        No trade opportunities to show. Check back later for new listings.
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Opportunity</TableHead>
          <TableHead>Entry price</TableHead>
          <TableHead>Target price</TableHead>
          <TableHead>Minimum</TableHead>
          <TableHead>Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {trades.map((trade) => (
          <TableRow key={trade.id}>
            <TableCell>
              <div className="trade-opportunity-copy">
                <strong>
                  {trade.title}
                  {trade.isDemo && <Badge variant="warning">Demo</Badge>}
                </strong>
                <span>{trade.symbol}</span>
                {trade.description && <small>{trade.description}</small>}
              </div>
            </TableCell>
            <TableCell>{formatCurrency(parseAmount(trade.entryPrice))}</TableCell>
            <TableCell>
              {trade.targetPrice
                ? formatCurrency(parseAmount(trade.targetPrice))
                : "--"}
            </TableCell>
            <TableCell>{formatCurrency(parseAmount(trade.minimumInvestment))}</TableCell>
            <TableCell>
              <div className="trade-row-actions">
                {trade.status === "open" ? (
                  <TradeActionForm
                    action="take"
                    actionUrl={actionUrl}
                    csrfToken={csrfToken}
                    tradeId={trade.id}
                    amount={(
                      <label className="trade-investment-field">
                        <span className="sr-only">Investment amount for {trade.symbol}</span>
                        <input
                          type="number"
                          name="amount"
                          min={trade.minimumInvestment}
                          step="0.01"
                          defaultValue={trade.minimumInvestment}
                          required
                        />
                      </label>
                    )}
                  >
                    <Button size="sm" type="submit">Take trade</Button>
                  </TradeActionForm>
                ) : (
                  <Badge variant="muted">Closed</Badge>
                )}
                <TradeActionForm
                  action={watchlistIds.has(trade.id) ? "unwatch" : "watch"}
                  actionUrl={actionUrl}
                  csrfToken={csrfToken}
                  tradeId={trade.id}
                >
                  <Button size="sm" variant="outline" type="submit">
                    {watchlistIds.has(trade.id) ? "Remove watch" : "Watch"}
                  </Button>
                </TradeActionForm>
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function TradePositionsTable({ positions, closed = false }) {
  if (!positions.length) {
    return (
      <p className="empty-state">
        {closed
          ? "You have no positions in closed trades."
          : "You have not joined any open trades yet."}
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Trade</TableHead>
          <TableHead>Entry price</TableHead>
          <TableHead>Invested</TableHead>
          {closed && <TableHead>Payout</TableHead>}
          <TableHead>Status</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {positions.map((position) => (
          <TableRow key={position.id}>
            <TableCell>
              <div className="trade-opportunity-copy">
                <strong>{position.trade.title}</strong>
                <span>{position.trade.symbol}</span>
              </div>
            </TableCell>
            <TableCell>{formatCurrency(parseAmount(position.trade.entryPrice))}</TableCell>
            <TableCell>{formatCurrency(parseAmount(position.amount))}</TableCell>
            {closed && (
              <TableCell>
                {position.paid
                  ? formatCurrency(parseAmount(position.payoutAmount))
                  : "Pending"}
              </TableCell>
            )}
            <TableCell>
              <Badge variant={position.paid ? "positive" : closed ? "warning" : "muted"}>
                {position.paid ? "Paid" : closed ? "Awaiting payout" : "Open"}
              </Badge>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function TradeSection({
  section,
  trades,
  positions,
  actionUrl,
  csrfToken,
  watchlistIds,
}) {
  const Icon = section.icon;
  const isOfferList = section.value === "available" || section.value === "watchlist";
  const isClosed = section.value === "closed";
  const sectionTrades = section.value === "watchlist"
    ? trades.filter((trade) => watchlistIds.has(trade.id))
    : trades;
  const sectionPositions = positions.filter((position) =>
    isClosed
      ? position.status === "closed"
      : position.status === "open",
  );

  return (
    <Card className="trade-section-card">
      <CardHeader>
        <div className="trade-section-heading">
          <span className="trade-section-icon"><Icon size={16} /></span>
          <div>
            <CardTitle>{section.title}</CardTitle>
            <CardDescription>{section.description}</CardDescription>
          </div>
        </div>
        <Badge variant="muted">
          {isOfferList ? sectionTrades.length : sectionPositions.length}
        </Badge>
      </CardHeader>
      <CardContent className="table-content">
        {isOfferList ? (
          <TradeOpportunityTable
            trades={sectionTrades}
            actionUrl={actionUrl}
            csrfToken={csrfToken}
            watchlistIds={watchlistIds}
          />
        ) : (
          <TradePositionsTable positions={sectionPositions} closed={isClosed} />
        )}
      </CardContent>
    </Card>
  );
}

export function TradePage({
  openTrades = [],
  watchlist = [],
  positions = [],
  csrfToken = "",
  actionUrl = "",
  messages: pageMessages = [],
}) {
  const watchlistIds = new Set(watchlist.map((trade) => trade.id));

  return (
    <div className="creyp-dashboard trades-dashboard">
      <header className="dashboard-heading">
        <div>
          <p className="dashboard-eyebrow">Investment activity</p>
          <h1>Trades</h1>
          <p className="dashboard-subtitle">
            Review open opportunities and manage your trade positions.
          </p>
        </div>
        <Badge variant="warning">Internal wallet only</Badge>
      </header>

      {pageMessages.map((message, index) => (
        <div className={`trade-message trade-message-${message.level}`} role="status" key={`${index}-${message.text}`}>
          {message.text}
        </div>
      ))}

      <Tabs.Root defaultValue="available" className="dashboard-tabs trades-tabs">
        <Tabs.List aria-label="Trade sections">
          {tradeSections.map((section) => (
            <Tabs.Trigger value={section.value} key={section.value}>
              {section.label}
            </Tabs.Trigger>
          ))}
        </Tabs.List>
        {tradeSections.map((section) => (
          <Tabs.Content value={section.value} key={section.value}>
            <TradeSection
              section={section}
              trades={section.value === "watchlist" ? watchlist : openTrades}
              positions={positions}
              actionUrl={actionUrl}
              csrfToken={csrfToken}
              watchlistIds={watchlistIds}
            />
          </Tabs.Content>
        ))}
      </Tabs.Root>

      <Card className="brokerage-card" id="brokerage-accounts">
        <CardHeader>
          <div className="trade-section-heading">
            <span className="trade-section-icon"><Landmark size={16} /></span>
            <div>
              <CardTitle>Brokerage accounts</CardTitle>
              <CardDescription>Accounts connected for trade activity</CardDescription>
            </div>
          </div>
          <Badge variant="muted">Not connected</Badge>
        </CardHeader>
        <CardContent>
          <div className="brokerage-empty-state">
            <div>
              <strong>No brokerage accounts connected</strong>
              <p>Taking a trade deducts funds from your Creyp wallet; it does not place an order with a brokerage.</p>
            </div>
            <Button variant="outline" disabled type="button">
              <Plus size={15} /> Connect account
            </Button>
          </div>
        </CardContent>
      </Card>

      <p className="dashboard-data-note trade-data-note">
        Trade prices are listing information, not investment advice. Closed trades require an administrator to enter and pay out a settlement.
      </p>
    </div>
  );
}

export function Dashboard({ balance, invested, transactions = [], transactionCount = 0, userName, urls }) {
  const [balanceVisible, setBalanceVisible] = useState(true);
  const balanceValue = parseAmount(balance);
  const investedValue = parseAmount(invested);
  const displayName = userName || "there";

  return (
    <div className="creyp-dashboard">
      <header className="dashboard-heading">
        <div>
          <p className="dashboard-eyebrow">Personal account</p>
          <h1>Welcome back, {displayName}</h1>
          <p className="dashboard-subtitle">Here is your wallet and account activity at a glance.</p>
        </div>
        <Button asChild>
          <a href={urls.deposit}><Plus size={16} /> Add funds</a>
        </Button>
      </header>

      <Tabs.Root defaultValue="overview" className="dashboard-tabs">
        <Tabs.List aria-label="Dashboard views">
          <Tabs.Trigger value="overview">Overview</Tabs.Trigger>
          <Tabs.Trigger value="transactions">Transactions</Tabs.Trigger>
        </Tabs.List>

        <Tabs.Content value="overview">
          <div className="dashboard-stat-grid">
            <StatCard
              label="Wallet balance"
              value={balanceVisible ? formatCurrency(balanceValue) : "••••••"}
              detail="Available account balance"
              icon={WalletCards}
              action={(
                <button className="balance-toggle" type="button" onClick={() => setBalanceVisible((visible) => !visible)} aria-label={balanceVisible ? "Hide balance" : "Show balance"}>
                  {balanceVisible ? <Eye size={14} /> : <EyeOff size={14} />}
                  {balanceVisible ? "Hide balance" : "Show balance"}
                </button>
              )}
            />
            <StatCard
              label="Amount invested"
              value={formatCurrency(investedValue)}
              detail="Total recorded by your account"
              icon={Activity}
            />
            <StatCard
              label="Transactions"
              value={new Intl.NumberFormat("en-US").format(transactionCount)}
              detail="Recorded account activity"
              icon={ArrowRight}
            />
          </div>

          <div className="dashboard-content-grid">
            <MarketChart />
            <Card className="actions-card">
              <CardHeader>
                <CardTitle>Quick actions</CardTitle>
                <CardDescription>Common account tasks</CardDescription>
              </CardHeader>
              <CardContent className="quick-actions">
                <Button asChild variant="outline" className="action-link">
                  <a href={urls.deposit}><ArrowDownLeft size={16} /> Deposit funds <ArrowRight className="action-arrow" size={15} /></a>
                </Button>
                <Button asChild variant="outline" className="action-link">
                  <a href={urls.payments}><ArrowUpRight size={16} /> Payment history <ArrowRight className="action-arrow" size={15} /></a>
                </Button>
                <Button asChild variant="ghost" className="action-link action-link-referral">
                  <a href={urls.referral}>Manage referrals <ArrowRight className="action-arrow" size={15} /></a>
                </Button>
                <div className="account-note"><WalletCards size={16} /><span>Bitcoin wallet activity is recorded in your account.</span></div>
              </CardContent>
            </Card>
          </div>

          <Card className="transactions-card">
            <CardHeader className="transactions-heading">
              <div>
                <CardTitle>Recent transactions</CardTitle>
                <CardDescription>Your latest account activity</CardDescription>
              </div>
              <Badge variant="muted">{transactionCount} total</Badge>
            </CardHeader>
            <CardContent className="table-content">
              <TransactionTable transactions={transactions} compact />
            </CardContent>
          </Card>
        </Tabs.Content>

        <Tabs.Content value="transactions">
          <Card className="transactions-card all-transactions-card">
            <CardHeader>
              <CardTitle>All transactions</CardTitle>
              <CardDescription>Account activity available in your transaction history</CardDescription>
            </CardHeader>
            <CardContent className="table-content">
              <TransactionTable transactions={transactions} />
            </CardContent>
          </Card>
        </Tabs.Content>
      </Tabs.Root>
      <footer className="dashboard-data-note">Market chart data is provided by CoinGecko and is separate from your wallet balance.</footer>
    </div>
  );
}