`timescale 1ns / 1ps

module cic_bank #(
    parameter CHANNELS   = 64,
    parameter ORDER      = 5,
    parameter RATIO      = 64,
    parameter WIDTH      = 32,
    parameter DATA_WIDTH = 24
) (
    input  wire                         clk,
    input  wire                         rst,
    input  wire                         pdm_valid,
    input  wire [CHANNELS-1:0]          pdm_bits,
    output reg                          out_valid,
    output reg  [$clog2(CHANNELS)-1:0]  out_channel,
    output reg  signed [DATA_WIDTH-1:0] out_sample
);

    localparam CHANNEL_WIDTH = $clog2(CHANNELS);
    localparam COUNT_WIDTH   = $clog2(RATIO);
    localparam GAIN_BITS     = ORDER * $clog2(RATIO);
    localparam INPUT_SHIFT   = GAIN_BITS + 1 - DATA_WIDTH;

    localparam signed [WIDTH-1:0] DATA_MAX = (1 <<< (DATA_WIDTH - 1)) - 1;

    reg [COUNT_WIDTH-1:0] phase;
    wire capture = pdm_valid && phase == RATIO - 1;

    always @(posedge clk) begin
        if (rst)
            phase <= 0;
        else if (pdm_valid)
            phase <= (phase == RATIO - 1) ? 0 : phase + 1'b1;
    end

    reg signed [WIDTH-1:0] snapshot [0:CHANNELS-1];

    genvar mic, stage;
    generate
        for (mic = 0; mic < CHANNELS; mic = mic + 1) begin : channel
            reg signed [WIDTH-1:0] integrator [0:ORDER-1];
            wire signed [WIDTH-1:0] level = pdm_bits[mic] ? 1 : -1;

            for (stage = 0; stage < ORDER; stage = stage + 1) begin : integrate
                wire signed [WIDTH-1:0] feed;

                if (stage == 0) begin : first_stage
                    assign feed = level;
                end else begin : later_stage
                    assign feed = integrator[stage-1];
                end

                always @(posedge clk) begin
                    if (rst)
                        integrator[stage] <= 0;
                    else if (pdm_valid)
                        integrator[stage] <= integrator[stage] + feed;
                end
            end

            always @(posedge clk)
                if (capture)
                    snapshot[mic] <= integrator[ORDER-1];
        end
    endgenerate

    reg                     scanning;
    reg [CHANNEL_WIDTH-1:0] scan_channel;

    always @(posedge clk) begin
        if (rst) begin
            scanning     <= 1'b0;
            scan_channel <= 0;
        end else if (!scanning) begin
            if (capture) begin
                scanning     <= 1'b1;
                scan_channel <= 0;
            end
        end else if (scan_channel == CHANNELS - 1) begin
            scanning <= 1'b0;
        end else begin
            scan_channel <= scan_channel + 1'b1;
        end
    end

    reg                     head_valid;
    reg [CHANNEL_WIDTH-1:0] head_channel;
    reg signed [WIDTH-1:0]  head_value;

    always @(posedge clk) begin
        head_valid   <= scanning && !rst;
        head_channel <= scan_channel;
        head_value   <= snapshot[scan_channel];
    end

    generate
        for (stage = 0; stage < ORDER; stage = stage + 1) begin : comb
            wire                     feed_valid;
            wire [CHANNEL_WIDTH-1:0] feed_channel;
            wire signed [WIDTH-1:0]  feed_value;

            if (stage == 0) begin : first_stage
                assign feed_valid   = head_valid;
                assign feed_channel = head_channel;
                assign feed_value   = head_value;
            end else begin : later_stage
                assign feed_valid   = comb[stage-1].valid_q;
                assign feed_channel = comb[stage-1].channel_q;
                assign feed_value   = comb[stage-1].value_q;
            end

            reg                     valid_q;
            reg [CHANNEL_WIDTH-1:0] channel_q;
            reg signed [WIDTH-1:0]  value_q;
            reg signed [WIDTH-1:0]  delay [0:CHANNELS-1];

            integer clear_index;
            initial
                for (clear_index = 0; clear_index < CHANNELS; clear_index = clear_index + 1)
                    delay[clear_index] = 0;

            always @(posedge clk) begin
                valid_q   <= feed_valid && !rst;
                channel_q <= feed_channel;
                value_q   <= feed_value - delay[feed_channel];
                if (feed_valid)
                    delay[feed_channel] <= feed_value;
            end
        end
    endgenerate

    wire signed [WIDTH-1:0] reduced = comb[ORDER-1].value_q >>> INPUT_SHIFT;
    wire signed [WIDTH-1:0] limited = (reduced > DATA_MAX) ? DATA_MAX : reduced;

    always @(posedge clk) begin
        if (rst) begin
            out_valid   <= 1'b0;
            out_channel <= 0;
            out_sample  <= 0;
        end else begin
            out_valid   <= comb[ORDER-1].valid_q;
            out_channel <= comb[ORDER-1].channel_q;
            out_sample  <= limited[DATA_WIDTH-1:0];
        end
    end

endmodule
