-- 创建股票基础信息表
CREATE TABLE IF NOT EXISTS stock_info (
    id SERIAL PRIMARY KEY,
    third_code VARCHAR(20) NOT NULL, -- 第三方代码 (如 000001.SZ)
    symbol VARCHAR(10) NOT NULL,     -- 股票代码 (如 000001)
    name VARCHAR(100) NOT NULL,      -- 股票名称
    area VARCHAR(50),                -- 所在地域
    industry VARCHAR(50),            -- 所属行业
    market VARCHAR(20),              -- 市场类型
    list_date DATE,                  -- 上市日期
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束
    CONSTRAINT uq_stock_third_code UNIQUE (third_code),
    CONSTRAINT uq_stock_symbol UNIQUE (symbol)
);

-- 创建索引
CREATE INDEX idx_stock_symbol ON stock_info(symbol);
CREATE INDEX idx_stock_industry ON stock_info(industry);
CREATE INDEX idx_stock_market ON stock_info(market);

-- 触发器：更新 updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_stock_info_modtime
    BEFORE UPDATE ON stock_info
    FOR EACH ROW
    EXECUTE PROCEDURE update_updated_at_column();
