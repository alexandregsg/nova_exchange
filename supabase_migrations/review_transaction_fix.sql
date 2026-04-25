-- ============================================
-- Per-Transaction Reviews Migration
-- Run this in Supabase SQL Editor
-- ============================================

-- Step 1: Add transaction_id column (nullable for backward compatibility)
ALTER TABLE public.reviews ADD COLUMN IF NOT EXISTS transaction_id UUID;

-- Step 2: Remove old "one review per seller" constraint
-- (ignore error if it doesn't exist)
ALTER TABLE public.reviews DROP CONSTRAINT IF EXISTS reviews_reviewer_id_seller_id_key;

-- Step 3: Add new "one review per transaction" constraint
-- Allows NULL transaction_id for existing reviews (backward compatible)
ALTER TABLE public.reviews ADD CONSTRAINT reviews_reviewer_id_transaction_id_key
  UNIQUE (reviewer_id, transaction_id);

-- Step 4: Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_reviews_transaction_id ON public.reviews(transaction_id);
