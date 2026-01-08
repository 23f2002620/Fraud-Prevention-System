package com.example.fraud;

public class TxnFeature {
  public String user_id;
  public long window_end_epoch_ms;

  public long txn_count_60s;
  public double total_amount_60s;
  public double avg_amount_60s;

  public TxnFeature() {}
}
