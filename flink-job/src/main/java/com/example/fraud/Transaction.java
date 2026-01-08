package com.example.fraud;

public class Transaction {
  public String txn_id;
  public String user_id;
  public double amount;
  public String currency;
  public String merchant_id;
  public String country;
  public String device_id;
  public String ip;
  public String ts; // ISO string from generator

  public Transaction() {}
}
