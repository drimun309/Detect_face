# Face Recognition

## Introduction

Face Recognition is a computer vision task of identifying and verifying a person from a digital image or video frame. Face recognition systems can be used for various applications such as security, surveillance, access control, and more.

This repository contains an **End-to-End Face Recognition API** implemented using [ONNX Runtime](https://onnxruntime.ai/), [PostgreSQL](https://www.postgresql.org/) ([pgvector](https://github.com/pgvector/pgvector)), and [FastAPI](https://fastapi.tiangolo.com/). We also combining [YOLOx](https://github.com/Megvii-BaseDetection/YOLOX) for face detection and [InsigtFace](https://github.com/deepinsight/insightface) for face recognition in ONNX format. With pgvector (a vector similarity search extension for PostgreSQL), we can store and search for face embeddings efficiently. Lastly, we use FastAPI to expose the face recognition API.

## Docker Image

We provide a production-ready Docker image for convenience. You can pull the image from [Docker Hub](https://hub.docker.com/repository/docker/ruhyadi/vision-fr/general) and run it directly. The details are as follows:

| Version | Docker Image               | Description                                                                             |
| ------- | -------------------------- | --------------------------------------------------------------------------------------- |
| v1.0.0  | `ruhyadi/vision-fr:v1.0.0` | Contains YOLOx_s model for face detection and MobileFaceNet model for face recognition. |

## Supported Models

The following models are supported in this repository:

### Face Detection

| Model Name   | Description                                                                                  | Input Shape       | Output Shape                               | Link                                                                                               |
| ------------ | -------------------------------------------------------------------------------------------- | ----------------- | ------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| YOLOx s face | YOLOx small model for face detection. Trained on WIDER FACE dataset. **ONNX NMS supported**. | (-1, 3, 640, 640) | (`num_dets`, `boxes`, `classes`, `scores`) | [yoloxs_face.onnx](https://github.com/ruhyadi/vision-fr/releases/download/v1.0.0/yoloxs_face.onnx) |

### Face Recognition

| Model Name    | Description                                                                                                                                                            | Input Shape       | Output Shape | Link                                                                                           |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | ------------ | ---------------------------------------------------------------------------------------------- |
| MobileFaceNet | MobileFaceNet model for face recognition. Trained on WebFace600K. Official model from [InsightFace](https://github.com/deepinsight/insightface/tree/master/model_zoo). | (-1, 3, 112, 112) | (-1, 512)    | [w600k_mbf.onnx](https://github.com/ruhyadi/vision-fr/releases/download/v1.0.0/w600k_mbf.onnx) |

## Getting Started

### Prerequisites

We recommend using Docker either for development or production. You can install Docker by following the instructions [here](https://docs.docker.com/get-docker/).

Next, you can clone this repository and navigate to the project directory:

```bash
git clone https://github.com/ruhyadi/vision-fr
cd vision-fr
```

### Stack (камеры, веб-UI, стримы)

Скопируйте `.env.example` в `.env`, `go2rtc/go2rtc.example.yaml` → `go2rtc/go2rtc.yaml`.

**Модели:** `assets/yoloxs_face.onnx`, `assets/w600k_mbf.onnx`, `assets/yolov8s.pt` (детекция человека, GPU через Ultralytics). Опционально ONNX: `yolo26n.onnx`. **buffalo_l** — `run_download_models.bat`.

**GPU (RTX 3060):** стек собирается через `dockerfile.gpu.prod`, в `.env` укажите `FR_PROVIDER=gpu` и `PERSON_DET_ENGINE_PATH=assets/yolov8s.pt`. Нужен [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html).

Запуск:

```bash
docker compose -f docker-compose.stack.yaml up -d --build
```

- Веб-интерфейс: `http://localhost:8081`
- Swagger API: `http://localhost:8081/api/` (через nginx → backend)

Опционально модели **buffalo_l** (SCRFD + ArcFace R50): `run_download_buffalo.bat` или `python scripts/download_buffalo_l.py`, затем в `.env` укажите пути `assets/buffalo_l/det_10g.onnx` и `assets/buffalo_l/w600k_r50.onnx`.

## API Endpoints

The details of endpoints can be found in the Swagger documentation. Here the brief description of the endpoints:

| Method | Endpoint                        | Description                                 |
| ------ | ------------------------------- | ------------------------------------------- |
| GET    | `/api/v1/engine/face`           | Get list of all faces data in the database. |
| POST   | `/api/v1/engine/face/register`  | Register a new face to the database.        |
| POST   | `/api/v1/engine/face/recognize` | Compare a face with the database.           |
| DELETE | `/api/v1/engine/face/{id}`      | Delete a face from the database.            |

## Acknowledgements

- [ONNX Runtime](https://onnxruntime.ai/): ONNX Runtime is a performance-focused scoring engine for Open Neural Network Exchange (ONNX) models.
- [PostgreSQL](https://www.postgresql.org/): PostgreSQL is a powerful, open-source object-relational database system.
- [pgvector](https://github.com/pgvector/pgvector): pgvector is a vector similarity search extension for PostgreSQL.
- [FastAPI](https://fastapi.tiangolo.com/): FastAPI is a modern, fast (high-performance), web framework for building APIs with Python.
- [YOLOx](https://github.com/Megvii-BaseDetection/YOLOX): YOLOX is a high-performance anchor-free YOLO with ONNX NMS supported.
- [InsigtFace](https://github.com/deepinsight/insightface): InsightFace is an open-source 2D and 3D face analysis toolkit.