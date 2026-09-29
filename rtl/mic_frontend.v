`timescale 1ns / 1ps

module mic_frontend #(
    parameter CHANNELS   = 64,
    parameter CIC_ORDER  = 5,
    parameter CIC_RATIO  = 64,
    parameter CIC_WIDTH  = 32,
    parameter DATA_WIDTH = 24,
    parameter COEF_FILE  = "fir_coefficients.hex"
) (
    input  wire                         clk,
    input  wire                         rst,
    input  wire                         pdm_valid,
    input  wire [CHANNELS-1:0]          pdm_bits,
    output wire                         out_valid,
    output wire [$clog2(CHANNELS)-1:0]  out_channel,
    output wire signed [DATA_WIDTH-1:0] out_sample
);

    wire                         cic_valid;
    wire [$clog2(CHANNELS)-1:0]  cic_channel;
    wire signed [DATA_WIDTH-1:0] cic_sample;

    cic_bank #(
        .CHANNELS(CHANNELS),
        .ORDER(CIC_ORDER),
        .RATIO(CIC_RATIO),
        .WIDTH(CIC_WIDTH),
        .DATA_WIDTH(DATA_WIDTH)
    ) cic (
        .clk(clk),
        .rst(rst),
        .pdm_valid(pdm_valid),
        .pdm_bits(pdm_bits),
        .out_valid(cic_valid),
        .out_channel(cic_channel),
        .out_sample(cic_sample)
    );

    fir_bank #(
        .CHANNELS(CHANNELS),
        .DATA_WIDTH(DATA_WIDTH),
        .COEF_FILE(COEF_FILE)
    ) fir (
        .clk(clk),
        .rst(rst),
        .in_valid(cic_valid),
        .in_channel(cic_channel),
        .in_sample(cic_sample),
        .out_valid(out_valid),
        .out_channel(out_channel),
        .out_sample(out_sample)
    );

endmodule
