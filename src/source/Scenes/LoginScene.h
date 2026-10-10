#pragma once

// LoginScene.h - Login scene management

#include "Core/Platform/WinCompat.h"
#include "Render/Textures/ZzzOpenglUtil.h"  // For vec3_t

// Login scene lifecycle
void ConfigureStandaloneMapPreview(bool enabled, int worldFolderNumber, const wchar_t* controlPath, const wchar_t* statePath);
bool IsStandaloneMapPreview();
bool ConsumeStandaloneMapPreviewTeleport(float& x, float& y);
void PublishStandaloneMapPreviewCamera(float x, float y, float z, float yaw);
void CreateLogInScene();
void NewMoveLogInScene();
bool NewRenderLogInScene(HDC hDC);

// Camera animation
void MoveCamera();
void MoveCharacterCamera(vec3_t Origin, vec3_t Position, vec3_t Angle);

// Character deletion
void DeleteCharacter();

// LoginScene camera accessors (for external use)
int GetLoginCameraCount();
int GetLoginCameraWalkCut();

// State variables (extern - defined in ZzzScene.cpp)
extern int DeleteGuildIndex;
