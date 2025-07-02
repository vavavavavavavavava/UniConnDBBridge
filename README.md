# UniConnDBBridge

あらゆる認証方式に対応した汎用 SQLAlchemy データベースマネージャ

[![PyPI version](https://badge.fury.io/py/uniconndbbridge.svg)](https://badge.fury.io/py/uniconndbbridge)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 概要

UniConnDBBridge は、さまざまなデータベースと認証方法をサポートする、SQLAlchemyベースの汎用的なデータベース接続管理ライブラリです。設定オブジェクト、URL文字列、または自動検出機能を使用して、同期および非同期のデータベースエンジンを簡単に作成および管理できます。

## 主な機能

- **複数データベース対応**: PostgreSQL, MySQL, SQLite, Oracle, SQL Server をサポート
- **同期・非同期サポート**: 同期処理 ( `DatabaseManager` ) と非同期処理 ( `AsyncDatabaseManager` ) の両方に対応
- **柔軟な設定**:
  - `DBConfig` データクラスによる詳細な設定
  - SQLAlchemy互換のURL文字列
  - 接続情報の自動検出機能
- **拡張可能な認証**:
  - 基本的なユーザー名/パスワード認証
  - SSL/TLS認証
  - 独自の認証プラグインを簡単に追加可能
- **接続プーリング**: パフォーマンス向上のための接続プーリングを標準でサポート
- **ユーティリティ**: テーブル名やカラム名の取得など、便利なユーティリティ機能を提供

## インストール

```bash
pip install uniconndbbridge
```

特定のデータベースドライバをインストールするには、extra を使用します。

```bash
# PostgreSQL (psycopg2)
pip install "uniconndbbridge[postgres]"

# MySQL (mysqlclient)
pip install "uniconndbbridge[mysql]"

# 非同期PostgreSQL (asyncpg)
pip install "uniconndbbridge[postgres_async]"
```

## クイックスタート

### 同期処理

#### 1. URL文字列を使用する場合

```python
from uniconndbbridge import DatabaseManager

# PostgreSQLに接続
db_url = "postgresql+psycopg2://user:password@host:port/database"
db_manager = DatabaseManager(url=db_url)

# 接続をテスト
if db_manager.test_connection():
    print("接続に成功しました！")

# クエリを実行
with db_manager.session() as session:
    result = session.execute("SELECT 1").scalar()
    print(f"クエリ結果: {result}")

# マネージャをクローズ
db_manager.close()
```

#### 2. `DBConfig` を使用する場合

```python
from uniconndbbridge import DatabaseManager, DBConfig

# 設定オブジェクトを作成
config = DBConfig(
    dialect="postgresql",
    user="your_user",
    password="your_password",
    host="localhost",
    database="your_db"
)

# DatabaseManager を初期化
db_manager = DatabaseManager(config=config)

# テーブル名を取得
table_names = db_manager.get_table_names()
print(f"テーブル: {table_names}")

db_manager.close()
```

### 非同期処理

#### URL文字列を使用する場合

```python
import asyncio
from uniconndbbridge.async_ import AsyncDatabaseManager

async def main():
    db_url = "postgresql+asyncpg://user:password@host:port/database"
    async_db_manager = AsyncDatabaseManager(url=db_url)

    if await async_db_manager.test_connection():
        print("非同期接続に成功しました！")

    async with async_db_manager.session() as session:
        result = await session.execute("SELECT 1")
        print(f"クエリ結果: {result.scalar_one()}")

    await async_db_manager.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## 認証

### SSL/TLS認証

`DBConfig` と `auth_plugin` を使用して、SSL/TLS認証を構成できます。

```python
from uniconndbbridge import DatabaseManager, DBConfig

config = DBConfig(
    dialect="postgresql",
    user="your_user",
    password="your_password",
    host="your_secure_host",
    database="your_db",
    auth_plugin="ssl",
    auth_options={
        "ssl_cert": "/path/to/client.crt",
        "ssl_key": "/path/to/client.key",
        "ssl_ca": "/path/to/ca.crt",
        "ssl_mode": "verify-full"
    }
)

db_manager = DatabaseManager(config=config)

# ... 処理 ...
```

## ライセンス

このプロジェクトは MITライセンス の下で公開されています。
