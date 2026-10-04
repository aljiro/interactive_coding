"""Pydantic request/response models for the public API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MetricSpecOut(BaseModel):
    key: str
    label: str
    higher_is_better: bool
    format: str
    description: str = ""


class SubmissionTypeOut(BaseModel):
    id: str
    label: str
    accepted_extensions: list[str]
    description: str


class ChallengeSummary(BaseModel):
    id: str
    title: str
    short_description: str
    submission_type: str
    evaluator: str
    visualization: str
    primary_metric: MetricSpecOut
    secondary_metrics: list[MetricSpecOut]
    # Every adapter the challenge allows; a session may enable a subset of them.
    submission_types: list[SubmissionTypeOut]


class ResourceOut(BaseModel):
    name: str
    description: str
    content_type: str
    submission_types: list[str] | None = None  # None = relevant for every submission type


class ChallengeDetail(ChallengeSummary):
    instructions_md: str
    submission_instructions_md: dict[str, str]
    resources: list[ResourceOut]
    visualization_config: dict[str, Any]


class SessionPublic(BaseModel):
    id: str
    name: str
    challenge_id: str
    challenge_title: str
    join_code: str
    accepting_submissions: bool
    scores_hidden: bool
    enabled_submission_types: list[str]
    created_at: str | None


class SessionTeacherView(SessionPublic):
    n_participants: int
    n_submissions: int


class SessionCreate(BaseModel):
    challenge_id: str
    name: str = Field(default="", max_length=200)
    join_code: str | None = Field(
        default=None, min_length=4, max_length=12, pattern=r"^[A-Za-z0-9]+$"
    )


class SessionUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    accepting_submissions: bool | None = None
    scores_hidden: bool | None = None
    enabled_submission_types: list[str] | None = None


class JoinRequest(BaseModel):
    join_code: str = Field(min_length=3, max_length=16)
    display_name: str = Field(min_length=1, max_length=60)
    student_identifier: str | None = Field(default=None, max_length=100)


class ParticipantLive(BaseModel):
    id: str
    display_name: str
    joined_at: str | None
    n_submissions: int
    n_succeeded: int
    best_score: float | None
    best_metrics: dict[str, Any] | None
    best_submission_id: str | None
    best_at: str | None
    latest_submission_id: str | None
    latest_status: str | None
    latest_at: str | None
    latest_score: float | None
    rank: int | None = None
    improved: bool | None = None


class JoinResponse(BaseModel):
    token: str
    participant: ParticipantLive
    session: SessionPublic


class SubmissionPublic(BaseModel):
    id: str
    session_id: str
    participant_id: str
    seq_no: int
    status: str
    submission_type: str
    original_filename: str
    size_bytes: int
    created_at: str | None
    started_at: str | None
    finished_at: str | None
    error_message: str | None
    error_details: list[str]
    primary_score: float | None
    metrics: dict[str, Any] | None


class LiveSnapshot(BaseModel):
    session: SessionPublic
    challenge: ChallengeSummary
    participants: list[ParticipantLive]
    last_event_id: int


class MeResponse(BaseModel):
    participant: ParticipantLive
    session: SessionPublic
    challenge: ChallengeSummary
    submissions: list[SubmissionPublic]
    scores_hidden: bool


class DisplayOut(BaseModel):
    visualization: str
    config: dict[str, Any]
    data: dict[str, Any]


class SubmissionDisplayOut(BaseModel):
    submission_id: str
    participant_id: str
    visualization: str
    data: dict[str, Any]


class Message(BaseModel):
    detail: str
