# Crypto Arbitrage Bot

A sophisticated Python-based cryptocurrency arbitrage bot designed to identify and execute cross-exchange trading opportunities through advanced market data processing and smart contract interfacing.

## Key Features

- Real-time price monitoring across multiple exchanges
- Arbitrage opportunity detection with customizable thresholds
- Advanced profit calculation considering fees and gas costs
- Uniswap V3 integration for DEX data
- Market dashboard with spot prices, liquidity pools, and gas metrics
- Support for automatic trade execution (with smart contracts)

## Local Development

To set up your local development environment, follow these steps:

1. Clone the repository
2. Create a virtual environment with Python 3.11+
3. Install the following dependencies:
   - ccxt
   - email-validator
   - flask
   - flask-sqlalchemy
   - gunicorn
   - psycopg2-binary
   - python-dotenv
   - sqlalchemy
   - trafilatura
   - web3
4. Configure your environment variables in a `.env` file with:
   ```
   DATABASE_URL=postgresql://your_user:your_password@localhost:5432/arbitrage_bot
   FLASK_SECRET_KEY=your_random_secret_key
   # Optional Ethereum provider URL
   WEB3_PROVIDER_URI=https://mainnet.infura.io/v3/your_infura_key
   ```
5. Start the application with `python main.py`

See the IDE-SETTINGS.md file for recommended VS Code configuration.

## License

MIT
