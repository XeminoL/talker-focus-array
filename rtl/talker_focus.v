`timescale 1ns / 1ps

module talker_focus #(
    parameter CHANNELS   = 64,
    parameter BEAM_TAPS  = 64,
    parameter DATA_WIDTH = 24,
    parameter COEF_WIDTH = 18,
    parameter COEF_FILE  = "fir_coefficients.hex"
) (
    input  wire                                          clk,
    input  wire                                          rst,
    input  wire                                          pdm_valid,
    input  wire [CHANNELS-1:0]                           pdm_bits,
    input  wire                                          coef_write,
    input  wire [$clog2(CHANNELS)+$clog2(BEAM_TAPS)-1:0] coef_address,
    input  wire signed [COEF_WIDTH-1:0]                  coef_data,
    input  wire [5:0]                                    shift,
    output wire                                          audio_valid,
    output wire signed [DATA_WIDTH-1:0]                  audio_sample
);

    wire                         front_valid;
    wire [$clog2(CHANNELS)-1:0]  front_channel;
    wire signed [DATA_WIDTH-1:0] front_sample;

    mic_frontend #(
        .CHANNELS(CHANNELS),
        .DATA_WIDTH(DATA_WIDTH),
        .COEF_FILE(COEF_FILE)
    ) frontend (
        .clk(clk),
        .rst(rst),
        .pdm_valid(pdm_valid),
        .pdm_bits(pdm_bits),
        .out_valid(front_valid),
        .out_channel(front_channel),
        .out_sample(front_sample)
    );

    beam_bank #(
        .CHANNELS(CHANNELS),
        .TAPS(BEAM_TAPS),
        .DATA_WIDTH(DATA_WIDTH),
        .COEF_WIDTH(COEF_WIDTH)
    ) beam (
        .clk(clk),
        .rst(rst),
        .coef_write(coef_write),
        .coef_address(coef_address),
        .coef_data(coef_data),
        .shift(shift),
        .in_valid(front_valid),
        .in_channel(front_channel),
        .in_sample(front_sample),
        .out_valid(audio_valid),
        .out_sample(audio_sample)
    );

endmodule
