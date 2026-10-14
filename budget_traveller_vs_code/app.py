import io
import random
import heapq
import pandas as pd
import streamlit as st
import networkx as nx
import plotly.graph_objects as go

st.set_page_config(page_title="Budget Traveller with Coupons", page_icon="✈️", layout="wide")

st.markdown("""
<style>
.stApp { background: #f5f9ff; }
.hero { background: linear-gradient(110deg,#123d70,#2674b8); padding: 22px 28px; border-radius: 16px; color: white; margin-bottom: 18px; }
.hero h1 { color: white; margin: 0; }
.hero p { color: #e7f2ff; margin-bottom: 0; }
.panel { background: white; padding: 16px; border: 1px solid #c8e2ff; border-radius: 13px; }
.metric { background: #dcfce7; border: 1px solid #86efac; padding: 18px; border-radius: 12px; text-align: center; }
</style>
<div class="hero">
<h1>✈️ Budget Traveller with Coupons</h1>
<p>Find the cheapest route with at most K intermediate stops and C coupons. Each coupon halves one flight fare (rounded down).</p>
</div>
""", unsafe_allow_html=True)

def shortest_route(n, flights, K, C):
    # State tracks number of flights, so at most K stops means at most K+1 flights.
    graph = [[] for _ in range(n + 1)]
    for u, v, p in flights:
        graph[u].append((v, p))
    max_flights = K + 1
    # Dijkstra over (city, flights_used, coupons_used); each flight can be discounted or not.
    pq = [(0, 1, 0, 0)]
    best = {(1, 0, 0): 0}
    prev = {}
    end_state = None
    while pq:
        cost, city, used_flights, used_coupons = heapq.heappop(pq)
        state = (city, used_flights, used_coupons)
        if cost != best.get(state):
            continue
        if city == n:
            end_state = state
            break
        if used_flights >= max_flights:
            continue
        for nxt, price in graph[city]:
            options = [(price, used_coupons, False)]
            if used_coupons < C:
                options.append((price // 2, used_coupons + 1, True))
            for added, new_coupons, coupon in options:
                ns = (nxt, used_flights + 1, new_coupons)
                nc = cost + added
                if nc < best.get(ns, float("inf")):
                    best[ns] = nc
                    prev[ns] = (state, (city, nxt, price, added, coupon))
                    heapq.heappush(pq, (nc, nxt, used_flights + 1, new_coupons))
    if end_state is None:
        return None
    steps = []
    cur = end_state
    while cur != (1, 0, 0):
        old, flight = prev[cur]
        steps.append(flight)
        cur = old
    steps.reverse()
    return best[end_state], steps

def make_graph(n, m, seed=42):
    rng = random.Random(seed)
    edges = set()
    # Ensure a backbone route exists when possible.
    for u in range(1, n):
        edges.add((u, u + 1))
    possible = [(u, v) for u in range(1, n + 1) for v in range(1, n + 1) if u != v]
    rng.shuffle(possible)
    for edge in possible:
        if len(edges) >= m:
            break
        edges.add(edge)
    flights = [(u, v, rng.randint(50, 700)) for u, v in sorted(edges)]
    return flights

def draw_graph(n, flights, steps, current_step=0):
    G = nx.DiGraph()
    G.add_nodes_from(range(1, n + 1))
    for u, v, p in flights:
        G.add_edge(u, v, price=p)
    # Layered layout is readable for directed city networks.
    pos = nx.spring_layout(G, seed=8, k=1.3)
    edge_x, edge_y, edge_text = [], [], []
    chosen = {(u, v): (i, info) for i, info in enumerate(steps)}
    for u, v, data in G.edges(data=True):
        x0, y0 = pos[u]; x1, y1 = pos[v]
        is_path = (u, v) in chosen
        idx, info = chosen.get((u, v), (-1, None))
        active = is_path and idx < current_step
        color = "#f5b400" if active else ("#b9c7d8" if not is_path else "#f59e0b")
        width = 4 if is_path else 1.5
        edge_x += [x0, x1, None]; edge_y += [y0, y1, None]
        edge_text.append(f"{u} → {v}: {data['price']}")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(width=1.5, color="#8a9bb0"), hoverinfo="none"))
    # Draw directed arrows and fare labels.
    for u, v, data in G.edges(data=True):
        x0, y0 = pos[u]; x1, y1 = pos[v]
        dx, dy = x1-x0, y1-y0
        is_path = (u,v) in chosen
        idx, info = chosen.get((u,v),(-1,None))
        active = is_path and idx < current_step
        color = "#f5b400" if active else ("#f59e0b" if is_path else "#536b87")
        fig.add_annotation(x=x1-dx*0.13, y=y1-dy*0.13, ax=x0+dx*0.13, ay=y0+dy*0.13,
                           xref="x", yref="y", axref="x", ayref="y",
                           showarrow=True, arrowhead=3, arrowsize=1.1, arrowwidth=2.5 if is_path else 1.3,
                           arrowcolor=color)
        mx, my = (x0+x1)/2, (y0+y1)/2
        label = str(data["price"])
        if is_path:
            label = f"{info[2]}→{info[3]}" if info[4] else str(info[2])
        fig.add_annotation(x=mx, y=my, text=label, showarrow=False, bgcolor="#fff8df" if is_path else "white",
                           bordercolor=color, borderwidth=1, font=dict(size=11, color="#183153"))
    node_x=[]; node_y=[]; node_colors=[]; node_text=[]
    for node in G.nodes():
        x,y=pos[node]; node_x.append(x); node_y.append(y)
        if node == 1: color="#22c55e"
        elif node == n: color="#ef4444"
        elif any((u == node or v == node) for u,v,_,_,_ in steps): color="#f59e0b"
        else: color="#7c9fc9"
        node_colors.append(color); node_text.append(f"City {node}")
    fig.add_trace(go.Scatter(x=node_x,y=node_y,mode="markers+text",text=[str(x) for x in G.nodes()],
        textposition="middle center",hovertext=node_text,hoverinfo="text",
        marker=dict(size=38,color=node_colors,line=dict(color="white",width=2)),
        textfont=dict(color="white",size=14)))
    fig.update_layout(height=570, margin=dict(l=10,r=10,t=20,b=10), showlegend=False,
        plot_bgcolor="white", paper_bgcolor="white", xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig

with st.sidebar:
    st.header("Input")
    mode = st.radio("Choose input method", ["Manual input", "Upload CSV", "Generate graph"])
    if mode == "Manual input":
        n = st.number_input("Number of cities (N)", min_value=2, max_value=50, value=5, step=1)
        k = st.number_input("Maximum stops (K)", min_value=0, max_value=49, value=2, step=1)
        c = st.number_input("Coupons (C)", min_value=0, max_value=20, value=2, step=1)
        default = "1,2,100\n1,3,500\n2,3,100\n2,4,200\n3,4,100\n3,5,400\n4,5,200"
        raw = st.text_area("Flights: u,v,price (one per line)", default, height=190)
        flights=[]
        valid=True
        try:
            for line in raw.strip().splitlines():
                parts=[x.strip() for x in line.replace(" ", ",").split(",") if x.strip()]
                if len(parts)!=3: raise ValueError("Each flight must have u,v,price.")
                u,v,p=map(int,parts)
                if not (1<=u<=n and 1<=v<=n and u!=v and p>=0): raise ValueError("Invalid city or price.")
                flights.append((u,v,p))
        except Exception as e:
            valid=False; st.error(str(e))
    elif mode == "Upload CSV":
        uploaded = st.file_uploader("Upload CSV with columns u,v,p", type=["csv"])
        k = st.number_input("Maximum stops (K)", min_value=0, max_value=49, value=2, step=1)
        c = st.number_input("Coupons (C)", min_value=0, max_value=20, value=2, step=1)
        flights=[]; valid=False; n=2
        if uploaded:
            try:
                df=pd.read_csv(uploaded)
                df.columns=[str(x).strip().lower() for x in df.columns]
                if not {"u","v","p"}.issubset(df.columns): raise ValueError("CSV must have columns named u,v,p")
                flights=[(int(r.u),int(r.v),int(r.p)) for r in df.itertuples()]
                n=max(max(u,v) for u,v,p in flights)
                valid=all(1<=u<=n and 1<=v<=n and u!=v and p>=0 for u,v,p in flights)
                st.dataframe(df, use_container_width=True)
            except Exception as e: st.error(f"Could not read CSV: {e}")
    else:
        n = st.number_input("Number of cities (N)", min_value=2, max_value=30, value=7, step=1)
        k = st.number_input("Maximum stops (K)", min_value=0, max_value=29, value=2, step=1)
        c = st.number_input("Coupons (C)", min_value=0, max_value=20, value=2, step=1)
        m = st.number_input("Number of flights (M)", min_value=int(n-1), max_value=min(int(n*(n-1)), 300), value=min(max(int(n+3),int(n-1)),min(int(n*(n-1)),300)), step=1)
        seed = st.number_input("Random seed", min_value=0, max_value=999999, value=42)
        flights=make_graph(int(n),int(m),int(seed)); valid=True
        st.caption("A random directed graph is generated. A connected backbone is included.")

if mode != "Upload CSV":
    valid = locals().get("valid", True)
if valid and flights:
    result = shortest_route(int(n), flights, int(k), int(c))
else:
    result = None

left, right = st.columns([1.65, 1])
with left:
    st.subheader("Flight Network")
    if not valid or not flights:
        st.info("Enter valid flight data or upload a CSV to view the network.")
    else:
        if result:
            total, steps = result
            st.plotly_chart(draw_graph(int(n), flights, steps, len(steps)), use_container_width=True)
        else:
            steps=[]; total=-1
            st.plotly_chart(draw_graph(int(n), flights, steps, 0), use_container_width=True)
with right:
    st.subheader("Minimum Cost")
    if not valid or not flights:
        st.warning("Waiting for valid input.")
    elif not result:
        st.error("No valid route within the stop limit.")
        st.metric("Minimum cost", "-1")
    else:
        total, steps = result
        st.markdown(f'<div class="metric"><h1 style="color:#047857;margin:0">{total}</h1><b>Minimum total cost</b></div>', unsafe_allow_html=True)
        route=[1]+[s[1] for s in steps]
        st.markdown("**Chosen path:** " + " → ".join(map(str,route)))
        st.write(f"**Intermediate stops used:** {max(0,len(steps)-1)} / {int(k)}")
        st.write(f"**Coupons used:** {sum(1 for s in steps if s[4])} / {int(c)}")

if valid and flights and result:
    total, steps = result
    st.divider()
    st.subheader("Journey animation / step-through")
    current = st.slider("Show journey through this many flights", 0, len(steps), len(steps))
    running=0
    for i, (u,v,original,paid,coupon) in enumerate(steps[:current], start=1):
        running += paid
        if coupon:
            st.markdown(f"**Flight {i}: City {u} → City {v}** · 🟡 Coupon used · Fare **{original} → {paid}** · Running cost **{running}**")
        else:
            st.markdown(f"**Flight {i}: City {u} → City {v}** · Fare **{paid}** · Running cost **{running}**")
    if current == 0:
        st.info("Journey not started. Move the slider to step through the chosen route.")

    st.divider()
    st.subheader("Export graph as CSV")
    out=[]
    chosen={(u,v):(original,paid,coupon) for u,v,original,paid,coupon in steps}
    for u,v,p in flights:
        info=chosen.get((u,v))
        out.append({"u":u,"v":v,"original_price":p,"on_path":"x" if info else "",
                    "coupon_used":"x" if info and info[2] else "",
                    "paid_price":info[1] if info else ""})
    out_df=pd.DataFrame(out)
    st.dataframe(out_df, use_container_width=True)
    csv=out_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download marked graph CSV", data=csv, file_name="budget_traveller_result.csv", mime="text/csv")
else:
    st.caption("CSV format for upload: header row u,v,p followed by one flight per row. Cities are numbered from 1 to N.")
