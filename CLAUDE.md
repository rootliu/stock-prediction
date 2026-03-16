# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Multi-project workspace containing an AI-powered stock prediction system (A-stock and HK-stock markets) and PyTorch educational tutorials.

## Project Structure

- **stock-prediction/client/** — React 18 + TypeScript frontend (Vite, Ant Design, ECharts, Zustand)
- **stock-prediction/ml-service/** — Python FastAPI backend (data collection via AKShare, technical indicators, ML models)
- **pytorchTutorial/** — PyTorch learning notebooks (tensors, CNNs, transformers, etc.)

## Development Commands

### Frontend (stock-prediction/client/)
```bash
cd stock-prediction/client
npm install          # install dependencies
npm run dev          # dev server on port 3000 (proxies /api to localhost:8000)
npm run build        # typecheck + production build (tsc && vite build)
npm run lint         # ESLint with zero warnings enforced (--max-warnings 0)
npm run preview      # preview production build
```

### Backend ML Service (stock-prediction/ml-service/)
```bash
cd stock-prediction/ml-service
pip install -r requirements.txt
python main.py                    # FastAPI server on port 8000
```

### Testing
```bash
# Python tests (pytest is configured but tests are not yet implemented)
cd stock-prediction/ml-service && pytest

# Frontend linting (no test runner configured yet)
cd stock-prediction/client && npm run lint
```

## Architecture

### Frontend-Backend Communication
The Vite dev server proxies all `/api` requests to `http://localhost:8000` (FastAPI). Both services must be running for full functionality.

### Backend API Structure
All endpoints live in `stock-prediction/ml-service/main.py`. Route pattern: `/api/v1/{market}/{resource}` where market is `a-stock` or `hk-stock`. Data collectors are singletons initialized lazily via factory functions in `data_collector/__init__.py`.

### Key Modules
- **data_collector/a_stock.py** and **hk_stock.py** — `AStockCollector` and `HKStockCollector` classes wrapping AKShare for real-time quotes, K-line data, index data, and capital flow
- **utils/indicators.py** — `TechnicalIndicators` class with static methods for all technical indicators (MA, EMA, MACD, KDJ, RSI, Bollinger Bands, etc.) operating on pandas Series
- **client/src/store/index.ts** — Zustand stores (`useAppStore`, `useSearchStore`) with localStorage persistence for watchlists and UI state
- **client/src/services/api.ts** — Axios client with endpoint functions for both A-stock and HK-stock markets
- **client/src/components/KLineChart.tsx** — ECharts-based candlestick chart component

### Frontend Conventions
- Path alias: `@/` maps to `src/`
- TypeScript strict mode enabled with `noUnusedLocals` and `noUnusedParameters`
- Styling: Tailwind CSS with custom stock colors (`stock-up`: red #f5222d, `stock-down`: green #52c41a — follows Chinese market convention)
- UI components from Ant Design 5.x

### Backend Conventions
- Python 3.10+ required
- Pydantic v2 models for request/response validation
- Async-capable FastAPI with CORS middleware
- Formatter: Black

## Development Phases

The project follows a phased roadmap (see `stock-prediction/docs/REQUIREMENTS.md`):
1. Project initialization + Data collection (in progress)
2. K-line charts + Technical indicators
3. Prediction model training (LSTM, multi-factor)
4. Backtesting system (Backtrader)
5. Integration and optimization
